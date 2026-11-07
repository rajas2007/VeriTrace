"""Integration tests for forensic fingerprint hardening and content hash identity (Part D)."""

from __future__ import annotations

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
from veritrace.application.services.investigation_service import InvestigationService
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.document import DocumentType, TextLayerType
from veritrace.domain.enums.forensic import (
    FindingCategory,
    ReviewDecisionType,
    ReviewStatus,
)
from veritrace.domain.value_objects.geometry import PageDimensions
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    PAGE_PREFIX,
    generate_id,
)
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def hardening_env(tmp_path: Path):
    """Set up database and services for fingerprint hardening tests."""
    db_path = tmp_path / "test_hardening.sqlite"
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
                name="Hardening Verification Org",
                industry_sector="DEFENSE",
                created_at=datetime.now(UTC),
            )
        )

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    inv_service = InvestigationService(uow_factory)

    return {
        "inv_service": inv_service,
        "uow_factory": uow_factory,
        "org_id": org_id,
        "tmp_path": tmp_path,
    }


def test_fingerprint_deterministic_and_incorporates_content_hash() -> None:
    fp1 = InvestigationService._compute_forensic_fingerprint(
        FindingCategory.SIGNATURE_VERIFICATION,
        "STROKE_DIVERGENCE",
        "page_1:ref_1",
        "100_200",
        content_hash="abc1234567890def",
    )
    fp2 = InvestigationService._compute_forensic_fingerprint(
        FindingCategory.SIGNATURE_VERIFICATION,
        "STROKE_DIVERGENCE",
        "page_1:ref_1",
        "100_200",
        content_hash="abc1234567890def",
    )
    fp_different_hash = InvestigationService._compute_forensic_fingerprint(
        FindingCategory.SIGNATURE_VERIFICATION,
        "STROKE_DIVERGENCE",
        "page_1:ref_1",
        "100_200",
        content_hash="fed0987654321cba",
    )

    assert fp1 == fp2
    assert fp1 != fp_different_hash
    assert len(fp1) == 16


def test_unchanged_content_reuses_finding_and_preserves_review(hardening_env: dict) -> None:
    svc: InvestigationService = hardening_env["inv_service"]
    uow_factory = hardening_env["uow_factory"]
    org_id: str = hardening_env["org_id"]
    tmp_path: Path = hardening_env["tmp_path"]

    inv = svc.create_investigation(
        InvestigationCreateDTO(
            title="Idempotency Test Case",
            reference_code="INV-HARD-001",
            organization_id=org_id,
        )
    )

    # Low res image to generate deterministic finding
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    img_path = tmp_path / "lowres_doc.png"
    cv2.imwrite(str(img_path), img)

    doc_id = generate_id(DOC_PREFIX)
    page_id = generate_id(PAGE_PREFIX)
    file_hash = "a" * 64

    with uow_factory() as uow:
        doc = Document.create(
            investigation_id=inv.id,
            original_filename="LowRes.png",
            file_hash_sha256=file_hash,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc_id,
            page_count=1,
            file_size_bytes=len(img.tobytes()),
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

    # Pass 1: generate finding
    findings1 = svc.run_forensic_analysis(inv.id, org_id, crops_dir=tmp_path / "crops")
    assert len(findings1) == 1
    f1 = findings1[0]
    assert f1.review_status == ReviewStatus.PENDING_REVIEW

    # Analyst confirms the finding
    reviewed = svc.review_finding(
        inv.id,
        ReviewFindingRequestDTO(
            finding_id=f1.id,
            decision=ReviewDecisionType.CONFIRMED,
            rationale="Analyst confirmed image resolution limitation.",
            reviewer_id="analyst_test",
        ),
        organization_id=org_id,
    )
    assert reviewed.review_status == ReviewStatus.CONFIRMED

    # Pass 2: Re-run identical analysis
    findings2 = svc.run_forensic_analysis(inv.id, org_id, crops_dir=tmp_path / "crops")
    assert len(findings2) == 1
    assert findings2[0].id == f1.id
    assert findings2[0].review_status == ReviewStatus.CONFIRMED


def test_changed_content_hash_creates_new_finding_without_overwriting(hardening_env: dict) -> None:
    svc: InvestigationService = hardening_env["inv_service"]
    uow_factory = hardening_env["uow_factory"]
    org_id: str = hardening_env["org_id"]
    tmp_path: Path = hardening_env["tmp_path"]

    inv = svc.create_investigation(
        InvestigationCreateDTO(
            title="Content Hash Identity Case",
            reference_code="INV-HARD-002",
            organization_id=org_id,
        )
    )

    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    img_path = tmp_path / "sample.png"
    cv2.imwrite(str(img_path), img)

    doc_id = generate_id(DOC_PREFIX)
    page_id = generate_id(PAGE_PREFIX)

    with uow_factory() as uow:
        doc = Document.create(
            investigation_id=inv.id,
            original_filename="Version1.png",
            file_hash_sha256="1111111111111111" * 4,
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            document_id=doc_id,
            page_count=1,
            file_size_bytes=len(img.tobytes()),
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

    # Pass 1: generate and confirm finding
    f1 = svc.run_forensic_analysis(inv.id, org_id, crops_dir=tmp_path / "crops")[0]
    svc.review_finding(
        inv.id,
        ReviewFindingRequestDTO(
            finding_id=f1.id,
            decision=ReviewDecisionType.CONFIRMED,
            rationale="Confirmed V1 observation.",
            reviewer_id="analyst_test",
        ),
        organization_id=org_id,
    )

    # Simulate document re-upload or modification with changed SHA-256 hash
    with uow_factory() as uow:
        d = uow.documents.get_by_id(doc_id, org_id)
        assert d is not None
        d.file_hash_sha256 = "9999999999999999" * 4
        uow.documents.update(d, org_id)
        uow.commit()

    # Pass 2: Analysis of modified document must yield a distinct finding
    svc.run_forensic_analysis(inv.id, org_id, crops_dir=tmp_path / "crops")
    all_findings = svc.list_findings(inv.id, org_id)

    # Must contain both the original confirmed finding and the new finding
    assert len(all_findings) == 2
    orig = next(f for f in all_findings if f.id == f1.id)
    assert orig.review_status == ReviewStatus.CONFIRMED

    new_finding = next(f for f in all_findings if f.id != f1.id)
    assert new_finding.review_status == ReviewStatus.PENDING_REVIEW
