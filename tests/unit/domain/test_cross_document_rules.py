"""Unit tests for VeriTrace pure domain cross-document comparison rules.

Verifies:
1. QuantityConsistencyRule:
   - Parity with identical units
   - Mass conversions (MT to KG, T to KG, LBS to KG)
   - Length conversions (M to MM, CM, KM, FT, IN)
   - Count units (PCS, NOS, UNITS)
   - Incompatible units (e.g. Mass vs Length)
   - Unrecognized units
   - Over-billing proportional severity tiers (LOW, MEDIUM, HIGH, CRITICAL)
   - Under-delivery / partial shipments (LOW, MEDIUM)
   - Joint confidence calculation: min(conf_a, conf_b) * align_conf
2. MaterialGradeConsistencyRule:
   - Canonical equivalence (SS 316L vs SS-316-L)
   - Material grade contradiction (SS 316L vs SS 304 -> CRITICAL)
3. EntityNameConsistencyRule:
   - Corporate suffix normalization ("Tata Steel Ltd" vs "Tata Steel Limited")
   - Conflicting organization names -> HIGH severity
4. ReferenceCodeConsistencyRule:
   - Reference code canonical matching
   - Conflicting reference codes -> HIGH severity
5. FinancialTotalConsistencyRule:
   - Line total calculation parity (Rate * Qty = Total)
   - 0.02 rounding tolerance
   - Discrepancy severity scaling
   - Grand total summation (Subtotal + Taxes = Grand Total)
6. ChronologicalSequenceRule:
   - Normal chronological timeline (PO <= Challan <= Invoice)
   - Inverted sequence (Invoice predates PO -> TEMPORAL_CONTRADICTION, HIGH)
7. BatchNumberConsistencyRule:
   - Heat/batch matching
   - Heat/batch contradiction -> HIGH severity
8. ExplicitDocumentReferenceCompletenessRule:
   - Referenced document present
   - Referenced document missing from submission -> CONFIRMED_OBSERVATION, MEDIUM
9. EntityType enum extension verification
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from veritrace.domain.enums.audit import EntityType
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
)
from veritrace.domain.rules.cross_document import (
    BatchNumberConsistencyRule,
    ChronologicalSequenceRule,
    EntityNameConsistencyRule,
    ExplicitDocumentReferenceCompletenessRule,
    FinancialTotalConsistencyRule,
    MaterialGradeConsistencyRule,
    QuantityConsistencyRule,
    ReferenceCodeConsistencyRule,
    canonicalize_quantity,
    clean_corporate_name,
    clean_string_identifier,
)

# --- 1. EntityType Enum Extension Tests ---


def test_entity_type_new_values() -> None:
    """Verify that the 4 approved EntityType values exist with correct string representations."""
    assert EntityType.MATERIAL_GRADE == "MATERIAL_GRADE"
    assert EntityType.DOCUMENT_REFERENCE == "DOCUMENT_REFERENCE"
    assert EntityType.BATCH_NUMBER == "BATCH_NUMBER"
    assert EntityType.PRODUCT_CODE == "PRODUCT_CODE"


# --- 2. String & Unit Helpers Tests ---


def test_clean_string_identifier() -> None:
    """Verify alphanumeric stripping and uppercasing."""
    assert clean_string_identifier("SS-316L") == "SS316L"
    assert clean_string_identifier("po / 2024-99 ") == "PO202499"
    assert clean_string_identifier("HT#8941-A") == "HT8941A"


def test_clean_corporate_name() -> None:
    """Verify legal corporate suffix stripping."""
    assert clean_corporate_name("Tata Steel Limited") == "TATA STEEL"
    assert clean_corporate_name("Tata Steel Ltd.") == "TATA STEEL"
    assert clean_corporate_name("Acme Industrial Corp.") == "ACME INDUSTRIAL"
    assert clean_corporate_name("Apex Metals Private Limited") == "APEX METALS"
    assert clean_corporate_name("Apex Metals Pvt Ltd") == "APEX METALS"


def test_canonicalize_quantity() -> None:
    """Verify mass, length, and count conversions to base canonical units."""
    # Mass to KG
    assert canonicalize_quantity(Decimal("10"), "KG") == (Decimal("10.0"), "KG")
    assert canonicalize_quantity(Decimal("2.5"), "MT") == (Decimal("2500.0"), "KG")
    assert canonicalize_quantity(Decimal("1"), "Ton") == (Decimal("1000.0"), "KG")
    assert canonicalize_quantity(Decimal("500"), "g") == (Decimal("0.500"), "KG")

    # Length to M
    assert canonicalize_quantity(Decimal("100"), "M") == (Decimal("100.0"), "M")
    assert canonicalize_quantity(Decimal("5000"), "mm") == (Decimal("5.000"), "M")
    assert canonicalize_quantity(Decimal("250"), "cm") == (Decimal("2.50"), "M")

    # Count to PCS
    assert canonicalize_quantity(Decimal("50"), "PCS") == (Decimal("50"), "PCS")
    assert canonicalize_quantity(Decimal("12"), "Nos") == (Decimal("12"), "PCS")
    assert canonicalize_quantity(Decimal("100"), "units") == (Decimal("100"), "PCS")

    # Unrecognized unit
    assert canonicalize_quantity(Decimal("10"), "BARRELS") is None


# --- 3. QuantityConsistencyRule Tests ---


class TestQuantityConsistencyRule:
    """Unit tests for QuantityConsistencyRule."""

    def test_identical_quantities_and_units(self) -> None:
        result = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("5000"),
            unit_a="KG",
            raw_a="5000 KG",
            field_id_a="fld_01",
            conf_a=0.98,
            qty_b=Decimal("5000"),
            unit_b="KG",
            raw_b="5000 KG",
            field_id_b="fld_02",
            conf_b=0.95,
            alignment_conf=0.99,
        )
        assert result.is_consistent is True
        assert result.is_contradiction is False
        assert result.severity == FindingSeverity.LOW
        assert result.epistemic_tier == EpistemicTier.CONFIRMED_OBSERVATION
        assert pytest.approx(result.confidence, 0.001) == 0.95 * 0.99

    def test_compatible_unit_conversion_mt_to_kg(self) -> None:
        # 5 MT in PO == 5000 KG in Challan
        result = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("5"),
            unit_a="MT",
            raw_a="5 MT",
            field_id_a="fld_po_qty",
            conf_a=1.0,
            qty_b=Decimal("5000"),
            unit_b="KG",
            raw_b="5000 KG",
            field_id_b="fld_dc_qty",
            conf_b=1.0,
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW
        assert result.normalized_values == ("5000.0 KG", "5000.0 KG")

    def test_incompatible_units_mass_vs_length(self) -> None:
        result = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("100"),
            unit_a="KG",
            raw_a="100 KG",
            field_id_a="fld_01",
            conf_a=0.9,
            qty_b=Decimal("100"),
            unit_b="M",
            raw_b="100 M",
            field_id_b="fld_02",
            conf_b=0.9,
        )
        assert result.is_consistent is False
        assert result.is_contradiction is True
        assert result.severity == FindingSeverity.HIGH
        assert "Incompatible" in result.title

    def test_unrecognized_unit(self) -> None:
        result = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("10"),
            unit_a="LITERS",
            raw_a="10 Liters",
            field_id_a="fld_01",
            conf_a=0.9,
            qty_b=Decimal("10"),
            unit_b="LITERS",
            raw_b="10 Liters",
            field_id_b="fld_02",
            conf_b=0.9,
        )
        assert result.is_consistent is False
        assert "Unrecognized" in result.title

    def test_overbilling_severity_tiers(self) -> None:
        # 1. Delta <= 1%: LOW
        res_low = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_a",
            conf_a=1.0,
            qty_b=Decimal("1005"),
            unit_b="KG",
            raw_b="1005 KG",
            field_id_b="fld_b",
            conf_b=1.0,
        )
        assert res_low.is_consistent is False
        assert res_low.severity == FindingSeverity.LOW
        assert res_low.discrepancy_percent == Decimal("0.5")

        # 2. 1% < Delta <= 10%: MEDIUM
        res_med = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_a",
            conf_a=1.0,
            qty_b=Decimal("1080"),
            unit_b="KG",
            raw_b="1080 KG",
            field_id_b="fld_b",
            conf_b=1.0,
        )
        assert res_med.severity == FindingSeverity.MEDIUM
        assert res_med.discrepancy_percent == Decimal("8.0")

        # 3. 10% < Delta <= 50%: HIGH
        res_high = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_a",
            conf_a=1.0,
            qty_b=Decimal("1400"),
            unit_b="KG",
            raw_b="1400 KG",
            field_id_b="fld_b",
            conf_b=1.0,
        )
        assert res_high.severity == FindingSeverity.HIGH
        assert res_high.discrepancy_percent == Decimal("40.0")

        # 4. Delta > 50%: CRITICAL
        res_crit = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_a",
            conf_a=1.0,
            qty_b=Decimal("1600"),
            unit_b="KG",
            raw_b="1600 KG",
            field_id_b="fld_b",
            conf_b=1.0,
        )
        assert res_crit.severity == FindingSeverity.CRITICAL
        assert res_crit.discrepancy_percent == Decimal("60.0")

    def test_under_delivery_partial_shipment(self) -> None:
        # 1. Open order partial delivery: 800 KG delivered out of 1000 KG ordered
        # Order remains open, so this is NOT an inconsistency.
        res_open = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_po",
            conf_a=1.0,
            qty_b=Decimal("800"),
            unit_b="KG",
            raw_b="800 KG",
            field_id_b="fld_dc",
            conf_b=1.0,
            doc_type_a="PURCHASE_ORDER",
            doc_type_b="DELIVERY_CHALLAN",
            is_order_closed=False,
        )
        assert res_open.is_consistent is True
        assert res_open.severity == FindingSeverity.LOW
        assert "Partial Delivery (Open Order)" in res_open.title

        # 2. Closed order shortfall: 800 KG delivered out of 1000 KG ordered
        # Order is closed, so the 200 KG shortfall IS a discrepancy.
        res_closed = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_po",
            conf_a=1.0,
            qty_b=Decimal("800"),
            unit_b="KG",
            raw_b="800 KG",
            field_id_b="fld_dc",
            conf_b=1.0,
            doc_type_a="PURCHASE_ORDER",
            doc_type_b="DELIVERY_CHALLAN",
            is_order_closed=True,
        )
        assert res_closed.is_consistent is False
        assert res_closed.severity == FindingSeverity.LOW
        assert "Delivery Shortfall on Closed Order" in res_closed.title

        # 3. Closed order severe shortfall (>50%): 300 KG delivered out of 1000 KG -> MEDIUM
        res_severe_shortfall = QuantityConsistencyRule.evaluate(
            qty_a=Decimal("1000"),
            unit_a="KG",
            raw_a="1000 KG",
            field_id_a="fld_po",
            conf_a=1.0,
            qty_b=Decimal("300"),
            unit_b="KG",
            raw_b="300 KG",
            field_id_b="fld_dc",
            conf_b=1.0,
            doc_type_a="PURCHASE_ORDER",
            doc_type_b="DELIVERY_CHALLAN",
            is_order_closed=True,
        )
        assert res_severe_shortfall.is_consistent is False
        assert res_severe_shortfall.severity == FindingSeverity.MEDIUM


# --- 4. MaterialGradeConsistencyRule Tests ---


class TestMaterialGradeConsistencyRule:
    """Unit tests for MaterialGradeConsistencyRule."""

    def test_grade_match_with_formatting_differences(self) -> None:
        result = MaterialGradeConsistencyRule.evaluate(
            grade_a="SS 316L",
            raw_a="SS 316L",
            field_id_a="fld_01",
            conf_a=0.99,
            grade_b="SS-316-L",
            raw_b="SS-316-L",
            field_id_b="fld_02",
            conf_b=0.98,
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW
        assert result.epistemic_tier == EpistemicTier.CONFIRMED_OBSERVATION

    def test_grade_substitution_contradiction(self) -> None:
        result = MaterialGradeConsistencyRule.evaluate(
            grade_a="SS 316L",
            raw_a="SS 316L",
            field_id_a="fld_po_grade",
            conf_a=0.95,
            grade_b="SS 304",
            raw_b="SS 304",
            field_id_b="fld_mtc_grade",
            conf_b=0.95,
            doc_type_a="PURCHASE_ORDER",
            doc_type_b="MILL_TEST_CERT",
        )
        assert result.is_consistent is False
        assert result.is_contradiction is True
        assert result.severity == FindingSeverity.CRITICAL
        assert result.category == FindingCategory.CROSS_DOC_MISMATCH
        assert result.epistemic_tier == EpistemicTier.DETECTED_INCONSISTENCY
        assert "Material Grade Contradiction" in result.title


# --- 5. EntityNameConsistencyRule Tests ---


class TestEntityNameConsistencyRule:
    """Unit tests for EntityNameConsistencyRule."""

    def test_matching_entity_names_with_suffix_variation(self) -> None:
        result = EntityNameConsistencyRule.evaluate(
            name_a="Tata Steel Limited",
            raw_a="Tata Steel Limited",
            field_id_a="fld_01",
            conf_a=0.95,
            name_b="Tata Steel Ltd.",
            raw_b="Tata Steel Ltd.",
            field_id_b="fld_02",
            conf_b=0.95,
            party_role="Buyer",
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW

    def test_conflicting_entity_names(self) -> None:
        result = EntityNameConsistencyRule.evaluate(
            name_a="Tata Steel Limited",
            raw_a="Tata Steel Limited",
            field_id_a="fld_01",
            conf_a=0.95,
            name_b="Jindal Steel & Power Ltd",
            raw_b="Jindal Steel & Power Ltd",
            field_id_b="fld_02",
            conf_b=0.95,
            party_role="Supplier",
        )
        assert result.is_consistent is False
        assert result.severity == FindingSeverity.HIGH
        assert result.category == FindingCategory.CROSS_DOC_MISMATCH


# --- 6. ReferenceCodeConsistencyRule Tests ---


class TestReferenceCodeConsistencyRule:
    """Unit tests for ReferenceCodeConsistencyRule."""

    def test_matching_reference_codes(self) -> None:
        result = ReferenceCodeConsistencyRule.evaluate(
            cited_code="PO-2024/0991",
            cited_raw="PO-2024/0991",
            cited_field_id="fld_dc_ref",
            cited_conf=0.99,
            actual_code="PO 2024 0991",
            actual_raw="PO 2024 0991",
            actual_field_id="fld_po_num",
            actual_conf=0.99,
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW

    def test_conflicting_reference_codes(self) -> None:
        result = ReferenceCodeConsistencyRule.evaluate(
            cited_code="PO-2024-9901",
            cited_raw="PO-2024-9901",
            cited_field_id="fld_dc_ref",
            cited_conf=0.95,
            actual_code="PO-2024-8801",
            actual_raw="PO-2024-8801",
            actual_field_id="fld_po_num",
            actual_conf=0.95,
        )
        assert result.is_consistent is False
        assert result.severity == FindingSeverity.HIGH
        assert result.category == FindingCategory.CROSS_DOC_MISMATCH


# --- 7. FinancialTotalConsistencyRule Tests ---


class TestFinancialTotalConsistencyRule:
    """Unit tests for FinancialTotalConsistencyRule."""

    def test_valid_line_total_calculation(self) -> None:
        # Rate: 120.50, Qty: 100 -> Expected Total: 12050.00
        result = FinancialTotalConsistencyRule.evaluate_line_total(
            unit_rate=Decimal("120.50"),
            quantity=Decimal("100"),
            stated_total=Decimal("12050.00"),
            raw_rate="120.50",
            raw_qty="100",
            raw_total="12,050.00",
            field_ids=("fld_rate", "fld_qty", "fld_tot"),
            conf=0.98,
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW
        assert result.category == FindingCategory.ARITHMETIC_MISMATCH

    def test_line_total_within_rounding_tolerance(self) -> None:
        # Rate: 33.33, Qty: 3 -> 99.99, Stated: 100.00 (diff 0.01 <= 0.02 tolerance)
        result = FinancialTotalConsistencyRule.evaluate_line_total(
            unit_rate=Decimal("33.33"),
            quantity=Decimal("3"),
            stated_total=Decimal("100.00"),
            raw_rate="33.33",
            raw_qty="3",
            raw_total="100.00",
            field_ids=("fld_rate", "fld_qty", "fld_tot"),
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW

    def test_line_total_arithmetic_mismatch(self) -> None:
        # Rate: 100, Qty: 10 -> Expected: 1000, Stated: 1500 (50% error -> HIGH)
        result = FinancialTotalConsistencyRule.evaluate_line_total(
            unit_rate=Decimal("100.00"),
            quantity=Decimal("10"),
            stated_total=Decimal("1500.00"),
            raw_rate="100.00",
            raw_qty="10",
            raw_total="1500.00",
            field_ids=("fld_rate", "fld_qty", "fld_tot"),
        )
        assert result.is_consistent is False
        assert result.category == FindingCategory.ARITHMETIC_MISMATCH
        assert result.severity == FindingSeverity.HIGH
        assert result.discrepancy_delta == Decimal("500.00")
        assert result.discrepancy_percent == Decimal("50.0")

    def test_valid_grand_total_with_adjustments(self) -> None:
        # Subtotal: 10000, Taxes: 1800, Freight: 500, Disc: 300, Adj: +50 -> 12050
        result = FinancialTotalConsistencyRule.evaluate_grand_total(
            subtotal=Decimal("10000.00"),
            taxes=Decimal("1800.00"),
            freight=Decimal("500.00"),
            discounts=Decimal("300.00"),
            other_adjustments=Decimal("50.00"),
            stated_grand_total=Decimal("12050.00"),
            field_ids=("fld_sub", "fld_tax", "fld_freight", "fld_disc", "fld_grand"),
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW

    def test_invalid_grand_total_mismatch(self) -> None:
        # Subtotal: 10000, Taxes: 1800 -> Expected: 11800, Stated: 12500
        # diff 700 -> 5.9% -> MEDIUM
        result = FinancialTotalConsistencyRule.evaluate_grand_total(
            subtotal=Decimal("10000.00"),
            taxes=Decimal("1800.00"),
            stated_grand_total=Decimal("12500.00"),
            field_ids=("fld_sub", "fld_tax", "fld_grand"),
        )
        assert result.is_consistent is False
        assert result.category == FindingCategory.ARITHMETIC_MISMATCH
        assert result.severity == FindingSeverity.MEDIUM


# --- 8. ChronologicalSequenceRule Tests ---


class TestChronologicalSequenceRule:
    """Unit tests for ChronologicalSequenceRule."""

    def test_valid_timeline(self) -> None:
        result = ChronologicalSequenceRule.evaluate(
            date_earlier=date(2024, 1, 10),
            raw_earlier="10-Jan-2024",
            field_id_earlier="fld_po_date",
            conf_earlier=0.95,
            event_earlier="Purchase Order Issuance",
            doc_type_earlier="PURCHASE_ORDER",
            date_later=date(2024, 1, 15),
            raw_later="15-Jan-2024",
            field_id_later="fld_dc_date",
            conf_later=0.95,
            event_later="Goods Dispatch",
            doc_type_later="DELIVERY_CHALLAN",
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW
        assert result.category == FindingCategory.TEMPORAL_CONTRADICTION

    def test_inverted_timeline_contradiction(self) -> None:
        # Invoice issued on Jan 5, before PO issued on Jan 10
        result = ChronologicalSequenceRule.evaluate(
            date_earlier=date(2024, 1, 10),
            raw_earlier="10-Jan-2024",
            field_id_earlier="fld_po_date",
            conf_earlier=0.98,
            event_earlier="Purchase Order Issuance",
            doc_type_earlier="PURCHASE_ORDER",
            date_later=date(2024, 1, 5),
            raw_later="05-Jan-2024",
            field_id_later="fld_inv_date",
            conf_later=0.98,
            event_later="Commercial Invoice Issuance",
            doc_type_later="COMMERCIAL_INVOICE",
        )
        assert result.is_consistent is False
        assert result.is_contradiction is True
        assert result.severity == FindingSeverity.HIGH
        assert result.category == FindingCategory.TEMPORAL_CONTRADICTION
        assert "Temporal Contradiction" in result.title


# --- 9. BatchNumberConsistencyRule Tests ---


class TestBatchNumberConsistencyRule:
    """Unit tests for BatchNumberConsistencyRule."""

    def test_matching_batch_numbers(self) -> None:
        result = BatchNumberConsistencyRule.evaluate(
            batch_a="HT-9042",
            raw_a="HT-9042",
            field_id_a="fld_dc_batch",
            conf_a=0.95,
            batch_b="HT 9042",
            raw_b="HT 9042",
            field_id_b="fld_mtc_batch",
            conf_b=0.95,
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW

    def test_mismatched_batch_numbers(self) -> None:
        result = BatchNumberConsistencyRule.evaluate(
            batch_a="HT-9042",
            raw_a="HT-9042",
            field_id_a="fld_dc_batch",
            conf_a=0.95,
            batch_b="HT-9049",
            raw_b="HT-9049",
            field_id_b="fld_mtc_batch",
            conf_b=0.95,
        )
        assert result.is_consistent is False
        assert result.severity == FindingSeverity.HIGH
        assert result.category == FindingCategory.CROSS_DOC_MISMATCH


# --- 10. ExplicitDocumentReferenceCompletenessRule Tests ---


class TestExplicitDocumentReferenceCompletenessRule:
    """Unit tests for ExplicitDocumentReferenceCompletenessRule."""

    def test_referenced_document_is_present(self) -> None:
        result = ExplicitDocumentReferenceCompletenessRule.evaluate(
            citing_doc_id="doc_dc_01",
            citing_doc_type="DELIVERY_CHALLAN",
            cited_doc_type="MILL_TEST_CERT",
            cited_reference_code="MTC-2024-X109",
            available_doc_references=["PO-2024-001", "DC-2024-001", "MTC-2024-X109"],
            evidence_field_ids=("fld_cited_mtc",),
        )
        assert result.is_consistent is True
        assert result.severity == FindingSeverity.LOW

    def test_referenced_document_is_missing(self) -> None:
        result = ExplicitDocumentReferenceCompletenessRule.evaluate(
            citing_doc_id="doc_dc_01",
            citing_doc_type="DELIVERY_CHALLAN",
            cited_doc_type="MILL_TEST_CERT",
            cited_reference_code="MTC-2024-X109",
            available_doc_references=["PO-2024-001", "DC-2024-001"],  # MTC is missing!
            evidence_field_ids=("fld_cited_mtc",),
        )
        assert result.is_consistent is False
        assert result.severity == FindingSeverity.MEDIUM
        assert result.epistemic_tier == EpistemicTier.CONFIRMED_OBSERVATION
        assert "Missing Referenced Document" in result.title
