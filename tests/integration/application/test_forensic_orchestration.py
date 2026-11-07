"""Integration tests for forensic capabilities orchestration."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.dto.investigation import (
    InvestigationCreateDTO,
    ReviewFindingRequestDTO,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.document import DocumentType, TextLayerType
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    ReviewDecisionType,
    ReviewStatus,
)
from veritrace.domain.exceptions.base import EntityNotFoundError
from veritrace.domain.value_objects.geometry import PageDimensions
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    PAGE_PREFIX,
    SIGREF_PREFIX,
    SUBJ_PREFIX,
    generate_id,
)
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.authorized_subject import AuthorizedSubjectModel
from veritrace.infrastructure.persistence.models.organization import (
    OrganizationModel,
)
from veritrace.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


@pytest.fixture
def forensic_env(tmp_path: Path):
    """Set up isolated migrated SQLite database and services for forensics."""
    db_path = tmp_path / "test_forensic_orch.sqlite"
    db_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(db_url)

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
                name="Forensic Test Authority Ltd",
                industry_sector="MANUFACTURING",
                created_at=datetime.now(UTC),
            )
        )

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    inv_service = InvestigationService(uow_factory)

    return {
        "uow_factory": uow_factory,
        "inv_service": inv_service,
        "org_id": org_id,
        "tmp_path": tmp_path,
    }


def _create_canvas_with_signature_and_patch(
    w: int = 800, h: int = 1000, add_clone: bool = True
) -> np.ndarray:
    """Create synthetic document canvas with cursive strokes and textured patch."""
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)

    # Draw simulated machine printed lines
    cv2.putText(
        canvas, "CERTIFICATE OF INSPECTION", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2
    )
    cv2.line(canvas, (50, 100), (w - 50, 100), (0, 0, 0), 1)

    # Draw candidate cursive handwritten signature strokes
    pts = np.array(
        [
            [150, 600],
            [170, 580],
            [200, 620],
            [230, 570],
            [260, 630],
            [290, 560],
            [330, 610],
            [360, 550],
            [400, 590],
            [440, 580],
        ],
        dtype=np.int32,
    )
    cv2.polylines(canvas, [pts], isClosed=False, color=(20, 20, 20), thickness=3)
    cv2.putText(
        canvas, "Authorized Signatory", (150, 640), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1
    )

    # Draw high-contrast textured feature patch for ORB copy-move detection
    if add_clone:
        for r in range(5):
            for c in range(5):
                color = (0, 0, 0) if (r + c) % 2 == 0 else (120, 120, 120)
                cv2.rectangle(
                    canvas, (550 + c * 20, 700 + r * 20), (565 + c * 20, 715 + r * 20), color, -1
                )
        cv2.circle(canvas, (600, 750), 30, (0, 0, 0), 2)

    return canvas


def test_forensic_low_resolution_quality_gate(forensic_env):
    """Verify that low-resolution pages trigger an epistemic quality limitation finding."""
    inv_service: InvestigationService = forensic_env["inv_service"]
    uow_factory = forensic_env["uow_factory"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Quality Limitation Test",
            reference_code="INV-QL-001",
            organization_id=org_id,
        )
    )

    # Create low resolution 100x100 image
    low_res_img = np.full((100, 100, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "low_res_p1.png"
    cv2.imwrite(str(img_path), low_res_img)

    doc_id = generate_id(DOC_PREFIX)
    page_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        doc = Document.create(
            investigation_id=inv.id,
            original_filename="low_res_scan.png",
            file_hash_sha256="a" * 64,
            mime_type="image/png",
            document_type=DocumentType.UNCLASSIFIED,
            document_id=doc_id,
            page_count=1,
            file_size_bytes=1000,
            storage_path=str(img_path),
        )
        page = DocumentPage.create(
            document_id=doc_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=100, height_pixels=100, dpi=72),
            image_storage_path=str(img_path),
            page_id=page_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(doc, org_id)
        uow.documents.add_page(page, org_id)
        uow.commit()

    findings = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=tmp_path / "crops",
    )

    assert len(findings) == 1
    f = findings[0]
    assert f.category == FindingCategory.SIGNATURE_VERIFICATION
    assert f.epistemic_tier == EpistemicTier.CONFIRMED_OBSERVATION
    assert "Low Resolution" in f.title
    assert "INSUFFICIENT_EVIDENCE" in f.narrative_explanation
    assert f.review_status == ReviewStatus.PENDING_REVIEW


def test_forensic_signature_and_copymove_detection(forensic_env):
    """Verify visual forensic scan detects signatures, clones, evidence, and audit."""
    inv_service: InvestigationService = forensic_env["inv_service"]
    uow_factory = forensic_env["uow_factory"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Forensic Verification Full Scan",
            reference_code="INV-FOR-002",
            organization_id=org_id,
        )
    )

    # Create two pages with identical textured patches (simulating digital copy-move)
    img1 = _create_canvas_with_signature_and_patch(add_clone=True)
    img2 = _create_canvas_with_signature_and_patch(add_clone=True)

    img1_path = tmp_path / "doc1_p1.png"
    img2_path = tmp_path / "doc2_p1.png"
    cv2.imwrite(str(img1_path), img1)
    cv2.imwrite(str(img2_path), img2)

    doc1_id = generate_id(DOC_PREFIX)
    doc2_id = generate_id(DOC_PREFIX)
    page1_id = generate_id(PAGE_PREFIX)
    page2_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d1 = Document.create(
            investigation_id=inv.id,
            original_filename="Contract_A.png",
            file_hash_sha256="b" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc1_id,
            page_count=1,
            file_size_bytes=len(img1.tobytes()),
            storage_path=str(img1_path),
        )
        p1 = DocumentPage.create(
            document_id=doc1_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img1_path),
            page_id=page1_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        d2 = Document.create(
            investigation_id=inv.id,
            original_filename="Contract_B.png",
            file_hash_sha256="c" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc2_id,
            page_count=1,
            file_size_bytes=len(img2.tobytes()),
            storage_path=str(img2_path),
        )
        p2 = DocumentPage.create(
            document_id=doc2_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img2_path),
            page_id=page2_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d1, org_id)
        uow.documents.add_page(p1, org_id)
        uow.documents.add(d2, org_id)
        uow.documents.add_page(p2, org_id)
        uow.commit()

    findings = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=tmp_path / "crops",
    )

    assert len(findings) > 0
    # Copy-move patch should be detected between doc1 and doc2
    cm_findings = [f for f in findings if f.category == FindingCategory.COPY_MOVE_CLONE]
    assert len(cm_findings) >= 1
    cm_f = cm_findings[0]
    assert cm_f.epistemic_tier == EpistemicTier.DETECTED_INCONSISTENCY
    assert cm_f.review_status == ReviewStatus.PENDING_REVIEW
    assert len(cm_f.evidence_ids) >= 2  # linked to both source and target crops

    # Verify Evidence entities persisted in database
    with uow_factory() as uow:
        ev_items = uow.evidence.list_by_investigation(inv.id, org_id)
        assert len(ev_items) >= 2
        for ev in ev_items:
            assert Path(ev.crop_image_path).is_file()

        # Verify audit trail records ANOMALY_FLAGGED
        events = uow.audit_events.list_by_investigation(inv.id, org_id)
        anomaly_events = [e for e in events if e.event_type == AuditEventType.ANOMALY_FLAGGED]
        assert len(anomaly_events) >= 1
        assert anomaly_events[0].actor_id == "forensic_engine"


def test_signature_comparison_against_reference_profile(forensic_env):
    """Verify signature comparison against an enrolled reference profile records divergence."""
    inv_service: InvestigationService = forensic_env["inv_service"]
    uow_factory = forensic_env["uow_factory"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Signature Reference Test",
            reference_code="INV-SIGREF-03",
            organization_id=org_id,
        )
    )

    img = _create_canvas_with_signature_and_patch(add_clone=False)
    img_path = tmp_path / "questioned_doc.png"
    cv2.imwrite(str(img_path), img)

    doc_id = generate_id(DOC_PREFIX)
    page_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d = Document.create(
            investigation_id=inv.id,
            original_filename="questioned_po.png",
            file_hash_sha256="d" * 64,
            mime_type="image/png",
            document_type=DocumentType.PURCHASE_ORDER,
            document_id=doc_id,
            page_count=1,
            file_size_bytes=len(img.tobytes()),
            storage_path=str(img_path),
        )
        p = DocumentPage.create(
            document_id=doc_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img_path),
            page_id=page_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d, org_id)
        uow.documents.add_page(p, org_id)
        uow.commit()

    # Create dummy reference crop and profile
    ref_crop_path = tmp_path / "reference_sig.png"
    ref_crop = np.full((120, 250, 3), 255, dtype=np.uint8)
    cv2.line(ref_crop, (20, 60), (220, 60), (0, 0, 0), 4)  # Straight line distinct from cursive
    cv2.imwrite(str(ref_crop_path), ref_crop)

    # Compute genuine reference embedding
    from veritrace.capabilities.forensics.signatures.verifier import SignatureVerifier

    verifier = SignatureVerifier()
    ref_embedding = verifier.compute_embedding(ref_crop_path)

    subj_id = generate_id(SUBJ_PREFIX)
    ref_id = generate_id(SIGREF_PREFIX)

    ref_profile = SignatureReferenceProfile(
        id=ref_id,
        subject_id=subj_id,
        organization_id=org_id,
        crop_image_path=str(ref_crop_path),
        sha256_hash=hashlib.sha256(ref_crop_path.read_bytes()).hexdigest(),
        source_document_ref="REF-SPECIMEN-01",
        consent_mandate_ref="MANDATE-2026-001",
        enrollment_date=datetime.now(UTC),
        embedding_vector=ref_embedding,
    )

    with uow_factory() as uow:
        subj_model = AuthorizedSubjectModel(
            id=subj_id,
            organization_id=org_id,
            full_name="Rajesh Sharma",
            designation="Quality Inspector",
            id_reference="EMP-IND-4091",
            created_at=datetime.now(UTC),
        )
        uow._session.add(subj_model)
        uow._session.flush()

        from veritrace.infrastructure.persistence.mappers.signature_reference_mapper import (
            SignatureReferenceMapper,
        )

        ref_model = SignatureReferenceMapper.to_model(ref_profile)
        uow._session.add(ref_model)
        uow.commit()

    findings = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        reference_profiles=[ref_profile],
        crops_dir=tmp_path / "crops",
    )

    sig_findings = [f for f in findings if f.category == FindingCategory.SIGNATURE_VERIFICATION]
    assert len(sig_findings) >= 1
    # Stroke divergence should be recorded against the reference
    divergence_finding = sig_findings[0]
    assert divergence_finding.signature_reference_id == ref_profile.id
    assert divergence_finding.epistemic_tier == EpistemicTier.DETECTED_INCONSISTENCY
    assert divergence_finding.review_status == ReviewStatus.PENDING_REVIEW


def test_forensic_analysis_tenant_isolation(forensic_env):
    """Verify cross-tenant investigation access is denied during forensic analysis."""
    inv_service: InvestigationService = forensic_env["inv_service"]
    org_id: str = forensic_env["org_id"]
    other_org_id = "org_22222222222222222222222222222222"

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Tenant Boundary Test",
            reference_code="INV-TENANT-04",
            organization_id=org_id,
        )
    )

    # Calling forensic analysis under an unauthorized organization must fail
    with pytest.raises(EntityNotFoundError):
        inv_service.run_forensic_analysis(
            investigation_id=inv.id,
            organization_id=other_org_id,
        )


def test_forensic_analysis_idempotency_preserves_findings_and_evidence(forensic_env):
    """Verify that running forensic analysis repeatedly does not multiply findings/crops."""
    uow_factory = forensic_env["uow_factory"]
    inv_service: InvestigationService = forensic_env["inv_service"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]
    crops_dir = tmp_path / "crops_idempotency"

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Idempotency Test",
            reference_code="INV-IDEMP-01",
            organization_id=org_id,
        )
    )

    img1 = _create_canvas_with_signature_and_patch(add_clone=True)
    img2 = _create_canvas_with_signature_and_patch(add_clone=True)
    img1_path = tmp_path / "idemp_page1.png"
    img2_path = tmp_path / "idemp_page2.png"
    cv2.imwrite(str(img1_path), img1)
    cv2.imwrite(str(img2_path), img2)

    doc1_id = generate_id(DOC_PREFIX)
    doc2_id = generate_id(DOC_PREFIX)
    page1_id = generate_id(PAGE_PREFIX)
    page2_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d1 = Document.create(
            investigation_id=inv.id,
            original_filename="Doc_A.png",
            file_hash_sha256="d" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc1_id,
            page_count=1,
            file_size_bytes=len(img1.tobytes()),
            storage_path=str(img1_path),
        )
        p1 = DocumentPage.create(
            document_id=doc1_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img1_path),
            page_id=page1_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        d2 = Document.create(
            investigation_id=inv.id,
            original_filename="Doc_B.png",
            file_hash_sha256="e" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc2_id,
            page_count=1,
            file_size_bytes=len(img2.tobytes()),
            storage_path=str(img2_path),
        )
        p2 = DocumentPage.create(
            document_id=doc2_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img2_path),
            page_id=page2_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d1, org_id)
        uow.documents.add_page(p1, org_id)
        uow.documents.add(d2, org_id)
        uow.documents.add_page(p2, org_id)
        uow.commit()

    # Run 1: Initial forensic scan
    findings_run1 = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=crops_dir,
    )
    count_run1 = len(findings_run1)
    assert count_run1 > 0

    with uow_factory() as uow:
        ev_run1 = uow.evidence.list_by_investigation(inv.id, org_id)
        ev_count1 = len(ev_run1)
        files_run1 = list(crops_dir.glob("*.png"))

    # Run 2: Repeated forensic scan on unchanged inputs
    findings_run2 = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=crops_dir,
    )
    count_run2 = len(findings_run2)
    assert count_run2 == count_run1

    with uow_factory() as uow:
        # Findings count in DB must remain strictly stable
        db_findings2 = uow.findings.list_by_investigation(inv.id, org_id)
        assert len(db_findings2) == count_run1

        # Evidence count in DB must remain strictly stable
        ev_run2 = uow.evidence.list_by_investigation(inv.id, org_id)
        assert len(ev_run2) == ev_count1

        # Files on disk must NOT have multiplied
        files_run2 = list(crops_dir.glob("*.png"))
        assert len(files_run2) == len(files_run1)


def test_forensic_idempotency_preserves_human_review_decisions(forensic_env):
    """Verify that repeated forensic analysis never alters or overwrites human reviews."""
    uow_factory = forensic_env["uow_factory"]
    inv_service: InvestigationService = forensic_env["inv_service"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]
    crops_dir = tmp_path / "crops_review_preservation"

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Review Preservation Case",
            reference_code="INV-REV-01",
            organization_id=org_id,
        )
    )

    img1 = _create_canvas_with_signature_and_patch(add_clone=True)
    img2 = _create_canvas_with_signature_and_patch(add_clone=True)
    img1_path = tmp_path / "rev_page1.png"
    img2_path = tmp_path / "rev_page2.png"
    cv2.imwrite(str(img1_path), img1)
    cv2.imwrite(str(img2_path), img2)

    doc1_id = generate_id(DOC_PREFIX)
    doc2_id = generate_id(DOC_PREFIX)
    page1_id = generate_id(PAGE_PREFIX)
    page2_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d1 = Document.create(
            investigation_id=inv.id,
            original_filename="Doc_Review_1.png",
            file_hash_sha256="f" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc1_id,
            page_count=1,
            file_size_bytes=len(img1.tobytes()),
            storage_path=str(img1_path),
        )
        p1 = DocumentPage.create(
            document_id=doc1_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img1_path),
            page_id=page1_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        d2 = Document.create(
            investigation_id=inv.id,
            original_filename="Doc_Review_2.png",
            file_hash_sha256="1" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc2_id,
            page_count=1,
            file_size_bytes=len(img2.tobytes()),
            storage_path=str(img2_path),
        )
        p2 = DocumentPage.create(
            document_id=doc2_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img2_path),
            page_id=page2_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d1, org_id)
        uow.documents.add_page(p1, org_id)
        uow.documents.add(d2, org_id)
        uow.documents.add_page(p2, org_id)
        uow.commit()

    # Initial scan
    findings = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=crops_dir,
    )
    target_finding = findings[0]
    assert target_finding.review_status == ReviewStatus.PENDING_REVIEW

    # Human adjudicates finding as CONFIRMED
    reviewed_dto = inv_service.review_finding(
        investigation_id=inv.id,
        request=ReviewFindingRequestDTO(
            finding_id=target_finding.id,
            decision=ReviewDecisionType.CONFIRMED,
            rationale="Verified signature divergence by lead forensic document examiner.",
            reviewer_id="analyst_lead",
        ),
        organization_id=org_id,
    )
    assert reviewed_dto.review_status == ReviewStatus.CONFIRMED
    assert len(reviewed_dto.review_decisions) == 1

    # Re-run forensic analysis
    findings_re_run = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=crops_dir,
    )

    # Assert reviewed finding is STILL CONFIRMED and has review decision intact
    matched = [f for f in findings_re_run if f.id == target_finding.id][0]
    assert matched.review_status == ReviewStatus.CONFIRMED
    assert len(matched.review_decisions) == 1
    assert matched.review_decisions[0].reviewer_id == "analyst_lead"
    assert (
        matched.review_decisions[0].rationale
        == "Verified signature divergence by lead forensic document examiner."
    )

    # Verify audit trail contains the HUMAN_REVIEW_CONFIRMED event
    with uow_factory() as uow:
        audits = uow.audit_events.list_by_investigation(inv.id, org_id)
        dec_events = [e for e in audits if e.event_type == AuditEventType.HUMAN_REVIEW_CONFIRMED]
        assert len(dec_events) == 1


def test_forensic_analysis_changed_inputs_generates_new_findings(forensic_env):
    """Verify that adding new pages generates new findings without corrupting existing ones."""
    uow_factory = forensic_env["uow_factory"]
    inv_service: InvestigationService = forensic_env["inv_service"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]
    crops_dir = tmp_path / "crops_changed_inputs"

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Changed Inputs Test",
            reference_code="INV-CHG-01",
            organization_id=org_id,
        )
    )

    img1 = _create_canvas_with_signature_and_patch(add_clone=True)
    img1_path = tmp_path / "chg_page1.png"
    cv2.imwrite(str(img1_path), img1)

    doc1_id = generate_id(DOC_PREFIX)
    page1_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d1 = Document.create(
            investigation_id=inv.id,
            original_filename="Initial_Doc.png",
            file_hash_sha256="2" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc1_id,
            page_count=1,
            file_size_bytes=len(img1.tobytes()),
            storage_path=str(img1_path),
        )
        p1 = DocumentPage.create(
            document_id=doc1_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img1_path),
            page_id=page1_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d1, org_id)
        uow.documents.add_page(p1, org_id)
        uow.commit()

    # Run 1: On single document
    run1 = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=crops_dir,
    )
    count1 = len(run1)

    # Now add Document 2
    img2 = _create_canvas_with_signature_and_patch(add_clone=True)
    img2_path = tmp_path / "chg_page2.png"
    cv2.imwrite(str(img2_path), img2)

    doc2_id = generate_id(DOC_PREFIX)
    page2_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d2 = Document.create(
            investigation_id=inv.id,
            original_filename="Second_Doc.png",
            file_hash_sha256="3" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc2_id,
            page_count=1,
            file_size_bytes=len(img2.tobytes()),
            storage_path=str(img2_path),
        )
        p2 = DocumentPage.create(
            document_id=doc2_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img2_path),
            page_id=page2_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d2, org_id)
        uow.documents.add_page(p2, org_id)
        uow.commit()

    # Run 2: Cross-analysis should now discover copy-move pattern correspondence
    run2 = inv_service.run_forensic_analysis(
        investigation_id=inv.id,
        organization_id=org_id,
        crops_dir=crops_dir,
    )
    assert len(run2) > count1
    cm_matches = [f for f in run2 if f.category == FindingCategory.COPY_MOVE_CLONE]
    assert len(cm_matches) >= 1
    # Check that copy-move title reflects neutral terminology
    assert "Visual Pattern Correspondence:" in cm_matches[0].title
    # Check that narrative includes epistemic limitation warning
    assert "Standard vendor logos, headers, or forms" in cm_matches[0].narrative_explanation
    assert "does NOT constitute proof of document tampering" in cm_matches[0].narrative_explanation


def test_forensic_analysis_failure_rollback_cleans_crops(forensic_env, monkeypatch):
    """Verify that midway failure unlinks newly created crops and rolls back DB."""
    uow_factory = forensic_env["uow_factory"]
    inv_service: InvestigationService = forensic_env["inv_service"]
    org_id: str = forensic_env["org_id"]
    tmp_path: Path = forensic_env["tmp_path"]
    crops_dir = tmp_path / "crops_failure_cleanup"

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Failure Rollback Case",
            reference_code="INV-FAIL-01",
            organization_id=org_id,
        )
    )

    img1 = _create_canvas_with_signature_and_patch(add_clone=True)
    img1_path = tmp_path / "fail_page1.png"
    cv2.imwrite(str(img1_path), img1)

    doc1_id = generate_id(DOC_PREFIX)
    page1_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        d1 = Document.create(
            investigation_id=inv.id,
            original_filename="Doc_Fail_1.png",
            file_hash_sha256="4" * 64,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc1_id,
            page_count=1,
            file_size_bytes=len(img1.tobytes()),
            storage_path=str(img1_path),
        )
        p1 = DocumentPage.create(
            document_id=doc1_id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=800, height_pixels=1000, dpi=150),
            image_storage_path=str(img1_path),
            page_id=page1_id,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )
        uow.documents.add(d1, org_id)
        uow.documents.add_page(p1, org_id)
        uow.commit()

    # Monkeypatch uow.commit to raise a RuntimeError before final persistence
    orig_commit = SqlAlchemyUnitOfWork.commit

    def failing_commit(self):
        raise RuntimeError("Simulated database failure during forensic commit")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", failing_commit)

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        inv_service.run_forensic_analysis(
            investigation_id=inv.id,
            organization_id=org_id,
            crops_dir=crops_dir,
        )

    # Verify no crop files remain on disk (they were unlinked on rollback)
    assert list(crops_dir.glob("*.png")) == []

    # Restore commit and check that database has 0 findings and 0 evidence for this investigation
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", orig_commit)
    with uow_factory() as uow:
        db_f = uow.findings.list_by_investigation(inv.id, org_id)
        db_e = uow.evidence.list_by_investigation(inv.id, org_id)
        assert len(db_f) == 0
        assert len(db_e) == 0
