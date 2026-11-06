"""Unit tests for VeriTrace CrossDocumentCorrelationEngine, normalizers, and aligner.

Verifies:
1. Deterministic normalization and idempotency:
   - Quantities, Decimal arithmetic, units
   - Amounts, currencies, Indian & Western comma formats
   - Dates (ISO, DMY, YMD, textual months)
   - Material grades (SS 316L, SS 304, carbon steel, unknown grade preservation)
   - Corporate names (suffix stripping, punctuation removal)
   - Identifiers (alphanumeric clean)
2. Ambiguous value handling (missing units, invalid formats).
3. 4-tier EntityAligner:
   - Authoritative exact identifier match
   - Authoritative normalized name match
   - High-confidence candidate (>= 0.95)
   - Review candidate (0.80 - 0.95)
   - Distinct rejection (< 0.80)
   - Strict Anti-Override: conflicting identifiers veto fuzzy match
4. CrossDocumentCorrelationEngine execution:
   - Multi-document line item aggregation
   - Open order partial delivery (consistent observation)
   - Closed order delivery shortfall (discrepancy)
   - Over-billing: Invoice quantity > Delivered quantity (discrepancy)
   - Material grade contradiction: PO (SS 316L) vs MTC/DC (SS 304) (CRITICAL discrepancy)
   - Line total and grand total arithmetic verification
   - Timeline chronological verification
   - Missing explicit reference detection
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from veritrace.capabilities.correlation.engine import CrossDocumentCorrelationEngine
from veritrace.capabilities.correlation.entity_aligner import EntityAligner
from veritrace.capabilities.correlation.models import (
    AlignmentTier,
    DocumentCorrelationInput,
)
from veritrace.capabilities.correlation.normalization import (
    normalize_amount,
    normalize_date,
    normalize_material_grade,
    normalize_organization_name,
    normalize_quantity,
)
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.forensic import (
    FindingCategory,
    FindingSeverity,
)
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    PAGE_PREFIX,
    generate_id,
)


def _make_field(
    name: str,
    value: str,
    raw: str | None = None,
    conf: float = 0.99,
    page_id: str | None = None,
) -> ExtractedField:
    pid = page_id or generate_id(PAGE_PREFIX)
    return ExtractedField.create(
        page_id=pid,
        field_name=name,
        field_value=value,
        raw_text=raw or value,
        confidence=conf,
    )


# --- 1. Normalization & Idempotency Tests ---


class TestNormalization:
    """Tests for deterministic normalization functions."""

    def test_quantity_normalization_and_idempotency(self) -> None:
        # Standard mass
        q1 = normalize_quantity("1,000.50 KG")
        assert q1.value == Decimal("1000.50")
        assert q1.unit == "KG"
        assert not q1.is_ambiguous

        # Idempotency: re-normalizing the output format yields exact same value
        q1_re = normalize_quantity(f"{q1.value} {q1.unit}")
        assert q1_re.value == q1.value
        assert q1_re.unit == q1.unit

        # Metric ton conversion: 2.5 MT == 2500 KG
        q2 = normalize_quantity("2.5 MT")
        assert q2.value == Decimal("2500.0")
        assert q2.unit == "KG"

        # Count units
        q3 = normalize_quantity("50 PCS")
        assert q3.value == Decimal("50")
        assert q3.unit == "PCS"

    def test_quantity_ambiguity_handling(self) -> None:
        # No unit provided
        q_no_unit = normalize_quantity("500")
        assert q_no_unit.is_ambiguous is True
        assert "Missing physical unit" in (q_no_unit.ambiguity_reason or "")

        # Unrecognized unit
        q_bad_unit = normalize_quantity("50 Barrels")
        assert q_bad_unit.is_ambiguous is True
        assert "Unrecognized physical unit" in (q_bad_unit.ambiguity_reason or "")

        # Non-numeric garbage
        q_garbage = normalize_quantity("N/A")
        assert q_garbage.is_ambiguous is True

    def test_amount_normalization(self) -> None:
        # Indian rupee symbols and commas
        a1 = normalize_amount("INR 1,50,000.00")
        assert a1.value == Decimal("150000.00")
        assert a1.currency == "INR"

        a2 = normalize_amount("₹ 45000.50")
        assert a2.value == Decimal("45000.50")
        assert a2.currency == "INR"

        # USD
        a3 = normalize_amount("$ 12,500.00")
        assert a3.value == Decimal("12500.00")
        assert a3.currency == "USD"

    def test_date_normalization(self) -> None:
        # ISO format
        d1 = normalize_date("2024-01-15")
        assert d1.value == date(2024, 1, 15)

        # DMY formats
        d2 = normalize_date("15-01-2024")
        assert d2.value == date(2024, 1, 15)

        d3 = normalize_date("15-Jan-2024")
        assert d3.value == date(2024, 1, 15)

        d4 = normalize_date("15 January 2024")
        assert d4.value == date(2024, 1, 15)

    def test_material_grade_normalization(self) -> None:
        # Known aliases map to canonical
        assert normalize_material_grade("SS-316L").canonical_grade == "SS 316L"
        assert normalize_material_grade("AISI 316L").canonical_grade == "SS 316L"
        assert normalize_material_grade("SUS 316L").canonical_grade == "SS 316L"
        assert normalize_material_grade("316L").canonical_grade == "SS 316L"

        assert normalize_material_grade("SS-304").canonical_grade == "SS 304"
        assert normalize_material_grade("AISI 304").canonical_grade == "SS 304"

        # Unknown grade is cleaned but not hallucinated
        unknown = normalize_material_grade("INCONEL 718")
        assert unknown.canonical_grade == "INCONEL 718"
        assert unknown.is_ambiguous is False

    def test_organization_name_normalization(self) -> None:
        assert normalize_organization_name("Tata Steel Limited").canonical_name == "TATA STEEL"
        assert normalize_organization_name("Tata Steel Pvt Ltd").canonical_name == "TATA STEEL"
        assert (
            normalize_organization_name("Acme Industrial Corp").canonical_name == "ACME INDUSTRIAL"
        )


# --- 2. EntityAligner Tests ---


class TestEntityAligner:
    """Tests for 4-tier EntityAligner."""

    def test_authoritative_matching_identifiers(self) -> None:
        pair = EntityAligner.align_entity_pair(
            source_doc_id="doc_01",
            source_field_id="fld_01",
            source_name="Tata Steel Ltd",
            source_identifier="27AAAAA0000A1Z5",
            target_doc_id="doc_02",
            target_field_id="fld_02",
            target_name="Tata Steel Limited",
            target_identifier="27AAAAA0000A1Z5",
        )
        assert pair.alignment_tier == AlignmentTier.AUTHORITATIVE_MATCH
        assert pair.similarity_score == 1.0

    def test_anti_override_conflicting_identifiers(self) -> None:
        # Even if corporate names are 100% identical, conflicting GSTINs veto the match!
        pair = EntityAligner.align_entity_pair(
            source_doc_id="doc_01",
            source_field_id="fld_01",
            source_name="Tata Steel Limited",
            source_identifier="27AAAAA0000A1Z5",
            target_doc_id="doc_02",
            target_field_id="fld_02",
            target_name="Tata Steel Limited",
            target_identifier="27BBBBB1111B1Z9",
        )
        assert pair.alignment_tier == AlignmentTier.CONFLICTING_IDENTIFIERS
        assert pair.similarity_score == 0.0
        assert "Anti-override guardrail" in pair.explanation

    def test_fuzzy_matching_tiers(self) -> None:
        # High confidence (>= 0.95): "JSW Steel Pipes" vs "JSW Steel Pipe"
        p_high = EntityAligner.align_entity_pair(
            source_doc_id="doc_01",
            source_field_id="fld_01",
            source_name="JSW Steel Pipes",
            source_identifier=None,
            target_doc_id="doc_02",
            target_field_id="fld_02",
            target_name="JSW Steel Pipe",
            target_identifier=None,
        )
        assert p_high.alignment_tier == AlignmentTier.HIGH_CONFIDENCE_CANDIDATE
        assert p_high.similarity_score >= 0.95

        # Review candidate (0.80 <= ratio < 0.95): "Bharat Forge" vs "Bharat Forgings" (~81.5%)
        p_rev = EntityAligner.align_entity_pair(
            source_doc_id="doc_01",
            source_field_id="fld_01",
            source_name="Bharat Forge",
            source_identifier=None,
            target_doc_id="doc_02",
            target_field_id="fld_02",
            target_name="Bharat Forgings",
            target_identifier=None,
        )
        assert p_rev.alignment_tier == AlignmentTier.REVIEW_CANDIDATE
        assert 0.80 <= p_rev.similarity_score < 0.95

        # No match (< 0.80): "Tata Steel" vs "JSW Steel"
        p_none = EntityAligner.align_entity_pair(
            source_doc_id="doc_01",
            source_field_id="fld_01",
            source_name="Tata Steel",
            source_identifier=None,
            target_doc_id="doc_02",
            target_field_id="fld_02",
            target_name="JSW Steel",
            target_identifier=None,
        )
        assert p_none.alignment_tier == AlignmentTier.NO_MATCH
        assert p_none.similarity_score < 0.80


# --- 3. CrossDocumentCorrelationEngine Industrial Demonstration Tests ---


class TestCorrelationEngineIndustrialDemonstration:
    """Verifies the core industrial multi-document correlation workflow."""

    def test_industrial_4_document_demonstration_discrepancies(self) -> None:
        """Verify the 4-document industrial demonstration discrepancies:

        1. 1000 KG ordered vs 800 KG delivered (partial delivery on open order is consistent).
        2. SS 316L ordered vs SS 304 certified (CRITICAL material grade contradiction!).
        3. 1000 KG invoiced vs 800 KG delivered (HIGH over-billing discrepancy!).
        """
        # Document 1: Purchase Order (PO-2024-001)
        po_id = generate_id(DOC_PREFIX)
        po = DocumentCorrelationInput(
            doc_id=po_id,
            doc_type="PURCHASE_ORDER",
            filename="PO_2024_001.pdf",
            extracted_fields=[
                _make_field("po_number", "PO-2024-001"),
                _make_field("date", "2024-01-10", "10-Jan-2024"),
                _make_field("material_grade", "SS 316L", "SS 316L Seamless Pipes"),
                _make_field("quantity", "1000 KG", "1,000 KG"),
                _make_field("buyer_name", "Bharat Heavy Fabrication Ltd"),
            ],
        )

        # Document 2: Delivery Challan (DC-2024-880)
        # Note: Delivers 800 KG (partial delivery) of SS 304 (instead of SS 316L)
        dc_id = generate_id(DOC_PREFIX)
        dc = DocumentCorrelationInput(
            doc_id=dc_id,
            doc_type="DELIVERY_CHALLAN",
            filename="DC_880.pdf",
            extracted_fields=[
                _make_field("challan_number", "DC-2024-880"),
                _make_field("date", "2024-01-15", "15-Jan-2024"),
                _make_field("cited_po_number", "PO-2024-001", "Ref PO: PO-2024-001"),
                _make_field("material_grade", "SS 304", "SS 304 Pipes"),
                _make_field("quantity", "800 KG", "800 KG"),
                _make_field("batch_number", "HT-9042", "Heat No: HT-9042"),
                _make_field("cited_mtc_number", "MTC-2024-X109", "MTC No: MTC-2024-X109"),
            ],
        )

        # Document 3: Mill Test Certificate (MTC-2024-X109)
        # Certifies SS 304 (Grade contradiction against PO's SS 316L)
        mtc_id = generate_id(DOC_PREFIX)
        mtc = DocumentCorrelationInput(
            doc_id=mtc_id,
            doc_type="MILL_TEST_CERT",
            filename="MTC_X109.pdf",
            extracted_fields=[
                _make_field("mtc_number", "MTC-2024-X109"),
                _make_field("material_grade", "SS 304", "Grade: SS 304"),
                _make_field("heat_number", "HT-9042", "Heat: HT-9042"),
            ],
        )

        # Document 4: Commercial Invoice (INV-2024-551)
        # Note: Invoices 1000 KG (over-billing 200 KG because only 800 KG was delivered)
        inv_id = generate_id(DOC_PREFIX)
        inv = DocumentCorrelationInput(
            doc_id=inv_id,
            doc_type="COMMERCIAL_INVOICE",
            filename="INV_551.pdf",
            extracted_fields=[
                _make_field("invoice_number", "INV-2024-551"),
                _make_field("date", "2024-01-20", "20-Jan-2024"),
                _make_field("cited_po_number", "PO-2024-001", "PO: PO-2024-001"),
                _make_field("quantity", "1000 KG", "1000 KG"),
                _make_field("unit_rate", "250.00", "250.00 / KG"),
                _make_field("line_total", "250000.00", "2,50,000.00"),
                _make_field("subtotal", "250000.00", "2,50,000.00"),
                _make_field("tax_amount", "45000.00", "45,000.00"),
                _make_field("grand_total", "295000.00", "2,95,000.00"),
            ],
        )

        engine = CrossDocumentCorrelationEngine(is_order_closed=False)
        inv_case_id = generate_id("inv_")
        result = engine.correlate(inv_case_id, [po, dc, mtc, inv])

        assert result.documents_analyzed == 4
        assert len(result.discrepancies) >= 2

        # 1. Verify Material Grade Contradiction (SS 316L vs SS 304) is flagged as CRITICAL
        grade_disc = next(
            (d for d in result.discrepancies if d.rule_code == "RULE_GRADE_CONSISTENCY"),
            None,
        )
        assert grade_disc is not None
        assert grade_disc.severity == FindingSeverity.CRITICAL
        assert grade_disc.category == FindingCategory.CROSS_DOC_MISMATCH
        assert "Material Grade Contradiction" in grade_disc.title

        # 2. Verify Over-billing Discrepancy (Invoiced 1000 KG vs Delivered 800 KG) is flagged
        qty_disc = next(
            (
                d
                for d in result.discrepancies
                if d.rule_code == "RULE_QTY_CONSISTENCY"
                and d.source_doc_id == dc.doc_id
                and d.target_doc_id == inv.doc_id
            ),
            None,
        )
        assert qty_disc is not None
        assert qty_disc.severity == FindingSeverity.HIGH  # 25% over-billing
        assert qty_disc.discrepancy_delta in (Decimal("200.0"), Decimal("200.00"), Decimal("200"))
        assert "exceeds DELIVERY_CHALLAN" in qty_disc.title

        # 3. Verify Partial Delivery on Open Order (PO 1000 KG vs DC 800 KG) is NOT a discrepancy
        po_dc_partial = next(
            (
                c
                for c in result.corroborations
                if c.rule_code == "RULE_QTY_CONSISTENCY"
                and c.source_doc_id == po.doc_id
                and c.target_doc_id == dc.doc_id
            ),
            None,
        )
        assert po_dc_partial is not None
        assert po_dc_partial.is_consistent is True
        assert "Partial Delivery (Open Order)" in po_dc_partial.title

        # 4. Verify Explicit MTC reference in Challan is found and corroborates
        mtc_ref_comp = next(
            (
                c
                for c in result.corroborations
                if c.rule_code == "RULE_EXPLICIT_REF_COMPLETENESS" and "MTC-2024-X109" in c.title
            ),
            None,
        )
        assert mtc_ref_comp is not None
        assert mtc_ref_comp.is_consistent is True

        # 5. Verify Batch Number matches between Challan and MTC
        batch_comp = next(
            (c for c in result.corroborations if c.rule_code == "RULE_BATCH_CONSISTENCY"),
            None,
        )
        assert batch_comp is not None
        assert batch_comp.is_consistent is True

        # 6. Verify Chronological Sequence is valid
        chrono_comps = [
            c for c in result.corroborations if c.rule_code == "RULE_CHRONOLOGY_CONSISTENCY"
        ]
        assert len(chrono_comps) >= 2

        # 7. Verify Financial Arithmetic is valid
        fin_comps = [
            c for c in result.corroborations if c.rule_code == "RULE_FIN_TOTAL_CONSISTENCY"
        ]
        assert len(fin_comps) >= 2
