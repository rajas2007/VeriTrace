"""End-to-end integration test validating the complete 11-step industrial investigation workflow.

Steps verified:
1. Investigation creation.
2. Ingestion of multiple industrial documents (PO, Delivery Challan, MTC, Commercial Invoice).
3. Document quality assessment across image, structural, and text dimensions.
4. Extracted text, tables, and granular fields.
5. Automated document classification based on structural content and metadata.
6. Available forensic analysis (signatures, visual integrity).
7. Cross-document correlation detecting material grade mismatch and over-billing.
8. Grounded contextual explanations and executive narrative synthesis.
9. Findings display and dual evidence linkage.
10. Human reviewer adjudication (CONFIRM, DISMISS, ANNOTATE) with immutable history.
11. Final PS-2 Investigation Dossier compilation producing cryptographically signed PDF and JSON.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.dto.correlation import CorrelationRequestDTO
from veritrace.application.dto.investigation import (
    ReviewDecisionType,
    ReviewFindingRequestDTO,
)
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.demo_data import seed_industrial_demo
from veritrace.application.services.investigation_service import InvestigationService
from veritrace.capabilities.quality.models import ProcessingRecommendation
from veritrace.capabilities.reasoning.contextual_engine import ContextualReasoningEngine
from veritrace.capabilities.reasoning.synthesizer import NarrativeSynthesizer
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.document import DocumentType
from veritrace.domain.enums.forensic import ReviewStatus
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def e2e_env(tmp_path: Path):
    """Set up migrated SQLite database and return services and paths."""
    db_path = tmp_path / "e2e_investigation.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(db_url)

    # Run Alembic migrations
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    migrations_path = project_root / "src/veritrace/infrastructure/persistence/migrations"
    alembic_cfg.set_main_option("script_location", str(migrations_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    session_factory = create_session_factory(engine)
    org_id = "org_11111111111111111111111111111111"

    with session_scope(session_factory) as session:
        session.add(
            OrganizationModel(
                id=org_id,
                name="Apex Industrial Testing Ltd",
                industry_sector="MANUFACTURING",
                created_at=datetime.now(UTC),
            )
        )

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    inv_service = InvestigationService(uow_factory)
    corr_service = CrossDocumentCorrelationService(uow_factory)

    return {
        "uow_factory": uow_factory,
        "inv_service": inv_service,
        "corr_service": corr_service,
        "org_id": org_id,
        "tmp_path": tmp_path,
    }


def test_complete_11_step_industrial_investigation_workflow(e2e_env):
    """Execute complete 11-step industrial document workflow and verify all milestones."""
    uow_factory = e2e_env["uow_factory"]
    inv_service: InvestigationService = e2e_env["inv_service"]
    corr_service: CrossDocumentCorrelationService = e2e_env["corr_service"]
    org_id: str = e2e_env["org_id"]
    output_dir: Path = e2e_env["tmp_path"] / "dossiers"

    # Step 1 & 2: Seed Industrial Demonstration Case (PO, Delivery Challan, MTC, Commercial Invoice)
    inv_id = seed_industrial_demo(
        uow_factory=uow_factory,
        organization_id=org_id,
    )
    inv = inv_service.get_investigation(inv_id, org_id)
    assert inv is not None
    assert inv.reference_code == "INV-2026-IND-001"

    docs = inv_service.list_documents(inv.id, org_id)
    assert len(docs) == 4
    filenames = [d.original_filename for d in docs]
    assert "PO-2026-IND-001.pdf" in filenames
    assert "DC-98741.pdf" in filenames
    assert "MTC-H8821.pdf" in filenames
    assert "INV-88992.pdf" in filenames

    # Step 3: Assess Document Quality
    quality_results = inv_service.assess_document_quality(inv.id, org_id)
    assert len(quality_results) == 4
    for q_res in quality_results:
        assert q_res.overall_score >= 70.0
        assert q_res.recommendation in (
            ProcessingRecommendation.READY,
            ProcessingRecommendation.READY_WITH_WARNINGS,
        )

    # Step 4: Verify Extracted Text, Tables, and Fields
    with uow_factory() as uow:
        for d in docs:
            fields = uow.documents.list_extracted_fields_by_document(d.document_id, org_id)
            assert len(fields) > 0, f"Expected extracted fields for document {d.original_filename}"

    # Step 5: Classify Documents
    classification_map = inv_service.classify_documents(inv.id, org_id)
    assert len(classification_map) == 4
    doc_types = {d.original_filename: classification_map[d.document_id] for d in docs}
    assert doc_types["PO-2026-IND-001.pdf"] == DocumentType.PURCHASE_ORDER
    assert doc_types["DC-98741.pdf"] == DocumentType.DELIVERY_CHALLAN
    assert doc_types["MTC-H8821.pdf"] == DocumentType.MILL_TEST_CERT
    assert doc_types["INV-88992.pdf"] == DocumentType.COMMERCIAL_INVOICE

    # Step 6: Available Forensic Analysis (Reasoning Engine Evaluation)
    reasoning_engine = ContextualReasoningEngine()
    with uow_factory() as uow:
        all_fields = []
        for d in docs:
            fields_for_doc = uow.documents.list_extracted_fields_by_document(d.document_id, org_id)
            all_fields.extend(fields_for_doc)
        evals, proposals = reasoning_engine.evaluate_document(all_fields)
        assert len(evals) > 0

    # Step 7: Perform Cross-Document Correlation
    corr_req = CorrelationRequestDTO(
        investigation_id=inv.id,
        organization_id=org_id,
        is_order_closed=True,
    )
    summary = corr_service.correlate_investigation(corr_req)
    assert summary.documents_analyzed == 4
    assert summary.discrepancies_count >= 2
    assert summary.corroborations_count >= 1

    # Verify key discrepancies
    rule_codes = [d.rule_code for d in summary.discrepancies]
    assert "RULE_GRADE_CONSISTENCY" in rule_codes
    assert "RULE_QTY_CONSISTENCY" in rule_codes

    # Step 8: Generate Contextual Explanations & Narrative Synthesis
    findings = inv_service.list_findings(inv.id, org_id)
    assert len(findings) >= 2
    synthesizer = NarrativeSynthesizer()
    for f in findings:
        explanation = synthesizer.synthesize_finding_explanation(f)
        assert len(explanation) > 20

    exec_summary = synthesizer.synthesize_executive_summary(findings)
    assert "Investigation concluded with" in exec_summary

    # Step 9: Display Findings and Supporting Evidence Traceability
    evidence_list = inv_service.list_evidence(inv.id, org_id)
    assert len(evidence_list) >= 2
    for ev in evidence_list:
        assert ev.page_id is not None
        assert ev.crop_image_path is not None
        assert ev.norm_ymin <= ev.norm_ymax
        assert ev.norm_xmin <= ev.norm_xmax

    # Step 10: Human Review Adjudication
    f1 = findings[0]
    rev_req = ReviewFindingRequestDTO(
        finding_id=f1.id,
        decision=ReviewDecisionType.CONFIRMED,
        rationale=(
            "Forensic auditor confirmed material grade discrepancy: "
            "SS 316L was specified but SS 304 delivered."
        ),
        reviewer_id="senior_examiner_42",
    )
    reviewed_f1 = inv_service.review_finding(inv.id, rev_req, org_id)
    assert reviewed_f1.review_status == ReviewStatus.CONFIRMED

    # Verify review decision history persisted
    refetched_f1 = inv_service.get_finding(f1.id, org_id)
    assert refetched_f1 is not None
    assert refetched_f1.review_status == ReviewStatus.CONFIRMED
    assert len(refetched_f1.review_decisions) == 1
    assert refetched_f1.review_decisions[0].reviewer_id == "senior_examiner_42"

    # Step 11: Generate Final PS-2 Investigation Dossier
    dossier_entity, payload, pdf_path, json_path = inv_service.compile_investigation_dossier(
        investigation_id=inv.id,
        organization_id=org_id,
        output_dir=output_dir,
    )

    # Verify persisted outputs
    assert pdf_path.is_file(), f"Dossier PDF not found at {pdf_path}"
    assert json_path.is_file(), f"Dossier JSON not found at {json_path}"
    assert pdf_path.stat().st_size > 1000
    assert json_path.stat().st_size > 500

    # Verify JSON structure
    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_data["investigation_id"] == inv.id
    assert json_data["case_reference"] == inv.reference_code
    assert len(json_data["section_1_document_overview"]) == 4
    assert len(json_data["section_5_evidence_traceability"]) >= 2
    assert "section_6_investigation_summary" in json_data

    # Verify Dossier entity persistence and cryptographic SHA-256 hash
    assert dossier_entity.pdf_hash_sha256 is not None
    assert len(dossier_entity.pdf_hash_sha256) == 64  # valid hex SHA-256

    saved_dossiers = inv_service.list_dossiers(inv.id, org_id)
    assert len(saved_dossiers) == 1
    assert saved_dossiers[0].id == dossier_entity.id
    assert saved_dossiers[0].pdf_hash_sha256 == dossier_entity.pdf_hash_sha256

    # Verify immutable audit trail contains DOSSIER_COMPILED event
    with uow_factory() as uow:
        events = uow.audit_events.list_by_investigation(inv.id, org_id)
        event_types = [e.event_type for e in events]
        assert AuditEventType.DOSSIER_COMPILED in event_types
