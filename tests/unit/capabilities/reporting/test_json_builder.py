"""Unit tests for JsonDossierBuilder PS-2 schema assembly."""

import json

from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.capabilities.reporting.json_builder import JsonDossierBuilder
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.document import DocumentStatus, DocumentType
from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory, FindingSeverity
from veritrace.domain.enums.investigation import InvestigationStatus, RiskClassification
from veritrace.domain.rules.base import RuleEvaluationResult
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    EVD_PREFIX,
    FLD_PREFIX,
    INV_PREFIX,
    PAGE_PREFIX,
    generate_id,
    utc_now,
)


def create_test_entities():
    """Helper creating minimal test domain entities."""
    inv = Investigation(
        id=generate_id(INV_PREFIX),
        title="Manufacturing Procurement Audit",
        reference_code="CASE-2026-0042",
        status=InvestigationStatus.PROCESSING,
        created_at=utc_now(),
        updated_at=utc_now(),
        risk_score=0.75,
        risk_classification=RiskClassification.SUSPECTED_MANIPULATION,
    )
    doc = Document(
        id=generate_id(DOC_PREFIX),
        investigation_id=inv.id,
        original_filename="Tax_Invoice_2026.pdf",
        file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="application/pdf",
        created_at=utc_now(),
        document_type=DocumentType.COMMERCIAL_INVOICE,
        page_count=2,
        file_size_bytes=45210,
        status=DocumentStatus.PROCESSED,
    )
    field = ExtractedField(
        id=generate_id(FLD_PREFIX),
        page_id=generate_id(PAGE_PREFIX),
        field_name="total_amount",
        field_value="1,25,000.00",
        raw_text="1,25,000.00",
        confidence=0.98,
    )
    rule_eval = RuleEvaluationResult(
        rule_name="LINE_ITEM_ARITHMETIC",
        category=FindingCategory.ARITHMETIC_MISMATCH,
        passed=False,
        discrepancy=500.0,
        expected_value=12000.0,
        observed_value=12500.0,
        explanation="Line item amount mismatch",
    )
    proposal = ForensicProposal(
        category=FindingCategory.ARITHMETIC_MISMATCH,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Arithmetic Error",
        narrative_explanation="Math error in line items.",
        confidence=1.0,
        measurements={"discrepancy": 500.0},
    )
    evidence = Evidence(
        id=generate_id(EVD_PREFIX),
        page_id=generate_id(PAGE_PREFIX),
        crop_image_path="dummy_crop.png",
        normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.2, ymax=0.3, xmax=0.4),
        grounding_explanation="Total amount bounding crop",
    )
    return inv, [doc], [field], [rule_eval], [proposal], [evidence]


def test_json_builder_assembles_all_six_sections():
    """Verify JsonDossierBuilder constructs valid 6-section PS-2 payload."""
    inv, docs, fields, rules, proposals, evs = create_test_entities()
    builder = JsonDossierBuilder()

    payload = builder.build_payload(
        investigation=inv,
        documents=docs,
        fields=fields,
        rule_evaluations=rules,
        findings_or_proposals=proposals,
        evidence_records=evs,
        executive_narrative="Investigation completed with 1 high severity arithmetic mismatch.",
    )

    # 1. Verification of Section 1: Document Overview
    assert len(payload.section_1_document_overview) == 1
    assert payload.section_1_document_overview[0].filename == "Tax_Invoice_2026.pdf"

    # 2. Verification of Section 2: Extracted Information
    assert len(payload.section_2_extracted_information) == 1
    assert payload.section_2_extracted_information[0].field_name == "total_amount"

    # 3. Verification of Section 3: Contextual Analysis
    assert len(payload.section_3_contextual_analysis) == 1
    assert payload.section_3_contextual_analysis[0].discrepancy == 500.0

    # 4. Verification of Section 4: Visual Forensics
    assert len(payload.section_4_visual_forensic_findings) == 1
    assert payload.section_4_visual_forensic_findings[0].category == "ARITHMETIC_MISMATCH"

    # 5. Verification of Section 5: Evidence Traceability
    assert len(payload.section_5_evidence_traceability) == 1
    assert payload.section_5_evidence_traceability[0].normalized_bbox["ymin"] == 0.1

    # 6. Verification of Section 6: Summary
    assert payload.section_6_investigation_summary.risk_score == 0.75
    assert payload.section_6_investigation_summary.risk_classification == "SUSPECTED_MANIPULATION"

    # Validate JSON serialization
    json_str = payload.to_json()
    parsed = json.loads(json_str)
    assert parsed["investigation_id"] == inv.id
    assert parsed["case_reference"] == "CASE-2026-0042"
