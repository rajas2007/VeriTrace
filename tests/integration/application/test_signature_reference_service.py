"""Integration tests for Signature Reference Management Application Service (Part A)."""

from __future__ import annotations

import concurrent.futures
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError

from veritrace.application.dto.investigation import InvestigationCreateDTO
from veritrace.application.dto.signature_reference import SignatureReferenceEnrollDTO
from veritrace.application.services.investigation_service import InvestigationService
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.exceptions.base import (
    EntityNotFoundError,
    TenantIsolationError,
    ValidationError,
)
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def service_env(tmp_path: Path):
    """Set up isolated migrated SQLite database and InvestigationService."""
    db_path = tmp_path / "test_sigref_service.sqlite"
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
    org_a = "org_11111111111111111111111111111111"
    org_b = "org_22222222222222222222222222222222"

    with session_scope(session_factory) as session:
        session.add(
            OrganizationModel(
                id=org_a,
                name="Tenant Alpha Corp",
                industry_sector="MANUFACTURING",
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            OrganizationModel(
                id=org_b,
                name="Tenant Beta Ltd",
                industry_sector="AEROSPACE",
                created_at=datetime.now(UTC),
            )
        )

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    inv_service = InvestigationService(uow_factory)

    # Create dummy high-res signature crop image
    img = np.ones((100, 250, 3), dtype=np.uint8) * 255
    cv2.ellipse(img, (120, 50), (80, 30), 15, 0, 360, (0, 0, 0), 2)
    cv2.line(img, (40, 60), (220, 40), (0, 0, 0), 2)
    crop_path = tmp_path / "valid_specimen.png"
    cv2.imwrite(str(crop_path), img)

    return {
        "service": inv_service,
        "uow_factory": uow_factory,
        "org_a": org_a,
        "org_b": org_b,
        "crop_path": crop_path,
        "tmp_path": tmp_path,
    }


def test_create_and_list_authorized_subjects(service_env: dict) -> None:
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]

    subject = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Elena Rostova",
        designation="Chief Quality Officer",
        id_reference="EMP-CQO-8411",
    )
    assert subject.id.startswith("subj_")
    assert subject.full_name == "Elena Rostova"
    assert subject.organization_id == org_a

    subjects = svc.list_authorized_subjects(org_a)
    assert len(subjects) == 1
    assert subjects[0].id == subject.id

    fetched = svc.get_authorized_subject(subject.id, org_a)
    assert fetched.full_name == "Elena Rostova"


def test_enroll_signature_reference_success(service_env: dict) -> None:
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    crop_path: Path = service_env["crop_path"]

    subject = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Dr. Marcus Vance",
        designation="Director of Engineering",
        id_reference="EMP-DOE-102",
    )

    inv = svc.create_investigation(
        InvestigationCreateDTO(
            title="Signature Governance Case",
            reference_code="CASE-SIG-2024-001",
            organization_id=org_a,
        )
    )

    dto = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id=subject.id,
        crop_image_path=str(crop_path),
        source_document_ref="Board Resolution 2024-C, Annex A",
        consent_mandate_ref="MANDATE-SIG-2024-099",
        investigation_id=inv.id,
    )

    ref = svc.enroll_signature_reference(dto)
    assert ref.id.startswith("sigref_")
    assert ref.subject_id == subject.id
    assert ref.organization_id == org_a
    assert ref.has_embedding is True
    assert len(ref.sha256_hash) == 64

    # Verify listing
    refs = svc.list_signature_references(org_a)
    assert len(refs) == 1
    assert refs[0].id == ref.id

    # Verify entity retrieval
    entity = svc.get_signature_reference(ref.id, org_a)
    assert entity is not None
    assert entity.id == ref.id
    assert entity.embedding_vector is not None

    # Verify audit event emitted
    with service_env["uow_factory"]() as uow:
        audits = uow.audit_events.list_by_investigation(
            investigation_id=inv.id,
            organization_id=org_a,
        )
        assert any(a.event_type.value == "SIGNATURE_ENROLLED" for a in audits)


def test_enroll_missing_file_raises_validation_error(service_env: dict) -> None:
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]

    subject = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Test Signer",
        designation="Auditor",
        id_reference="EMP-AUD-1",
    )

    dto = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id=subject.id,
        crop_image_path="/tmp/does_not_exist_image.png",
        source_document_ref="Doc Ref",
        consent_mandate_ref="Consent Ref",
    )

    with pytest.raises(ValidationError, match="not found"):
        svc.enroll_signature_reference(dto)


def test_enroll_nonexistent_subject_raises_entity_not_found(service_env: dict) -> None:
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    crop_path: Path = service_env["crop_path"]

    dto = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id="subj_00000000000000000000000000000000",
        crop_image_path=str(crop_path),
        source_document_ref="Doc Ref",
        consent_mandate_ref="Consent Ref",
    )

    with pytest.raises(EntityNotFoundError, match="AuthorizedSubject"):
        svc.enroll_signature_reference(dto)


def test_enroll_duplicate_specimen_is_idempotent(service_env: dict) -> None:
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    crop_path: Path = service_env["crop_path"]

    subject = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Elena Rostova",
        designation="CQO",
        id_reference="EMP-1",
    )

    dto = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id=subject.id,
        crop_image_path=str(crop_path),
        source_document_ref="Doc Ref",
        consent_mandate_ref="Consent Ref",
    )

    ref1 = svc.enroll_signature_reference(dto)
    ref2 = svc.enroll_signature_reference(dto)

    assert ref1.id == ref2.id
    refs = svc.list_signature_references(org_a)
    assert len(refs) == 1


def test_tenant_isolation_enforcement(service_env: dict) -> None:
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    org_b: str = service_env["org_b"]
    crop_path: Path = service_env["crop_path"]

    # Create subject in Org A
    subj_a = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Alpha Signer",
        designation="Manager",
        id_reference="ALPHA-1",
    )

    # Attempt to enroll under Org B using Org A's subject
    dto_cross = SignatureReferenceEnrollDTO(
        organization_id=org_b,
        subject_id=subj_a.id,
        crop_image_path=str(crop_path),
        source_document_ref="Cross Doc",
        consent_mandate_ref="Cross Consent",
    )
    with pytest.raises((EntityNotFoundError, TenantIsolationError)):
        svc.enroll_signature_reference(dto_cross)

    # Enroll legitimately under Org A
    dto_a = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id=subj_a.id,
        crop_image_path=str(crop_path),
        source_document_ref="Alpha Doc",
        consent_mandate_ref="Alpha Consent",
    )
    ref_a = svc.enroll_signature_reference(dto_a)

    # Org B cannot list or get Org A's references
    refs_b = svc.list_signature_references(org_b)
    assert len(refs_b) == 0

    with pytest.raises(TenantIsolationError):
        svc.get_signature_reference(ref_a.id, org_b)


def test_concurrent_duplicate_enrollment_with_threads(service_env: dict) -> None:
    """Verify simultaneous enrollment of identical specimens is thread-safe and idempotent."""
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    crop_path: Path = service_env["crop_path"]

    subj = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Marcus Vance",
        designation="VP Engineering",
        id_reference="EMP-VANCE-09",
    )

    dto = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id=subj.id,
        crop_image_path=str(crop_path),
        source_document_ref="Master Specimen Document 2026",
        consent_mandate_ref="Consent Mandate 2026-Vance",
    )

    # Launch 5 concurrent enrollment attempts across a thread pool
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(svc.enroll_signature_reference, dto) for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    assert len(results) == 5
    # All threads must receive a valid DTO with identical profile id and hash
    first_id = results[0].id
    first_hash = results[0].sha256_hash
    for r in results:
        assert r.id == first_id
        assert r.sha256_hash == first_hash

    # Database must contain exactly 1 reference row for this subject
    refs = svc.list_signature_references(org_a, subject_id=subj.id)
    assert len(refs) == 1
    assert refs[0].id == first_id


def test_database_level_unique_constraint_enforced_across_sessions(service_env: dict) -> None:
    """Verify SQLite database-level unique index blocks duplicates across sessions."""
    uow_factory = service_env["uow_factory"]
    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    crop_path: Path = service_env["crop_path"]

    import hashlib

    file_hash = hashlib.sha256(crop_path.read_bytes()).hexdigest()

    subj = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Direct DB Signer",
        designation="Auditor",
        id_reference="EMP-DB-01",
    )

    # First session inserts successfully
    with uow_factory() as uow1:
        p1 = SignatureReferenceProfile.create(
            subject_id=subj.id,
            organization_id=org_a,
            crop_image_path=str(crop_path),
            sha256_hash=file_hash,
            source_document_ref="Doc 1",
            consent_mandate_ref="Mandate 1",
        )
        uow1.signature_references.add(p1, org_a)
        uow1.commit()

    # Second session attempts to insert another profile with identical subject_id + sha256_hash
    with pytest.raises(IntegrityError), uow_factory() as uow2:
        p2 = SignatureReferenceProfile.create(
            subject_id=subj.id,
            organization_id=org_a,
            crop_image_path=str(crop_path),
            sha256_hash=file_hash,  # Same hash for same subject
            source_document_ref="Doc 2",
            consent_mandate_ref="Mandate 2",
        )
        uow2.signature_references.add(p2, org_a)
        uow2.commit()


def test_unrelated_database_error_not_swallowed_during_enrollment(service_env: dict) -> None:
    """Verify that unrelated database errors are not swallowed by duplicate resolution handler."""
    from unittest.mock import patch

    from veritrace.infrastructure.persistence.repositories.signature_reference_repository import (
        SqliteSignatureReferenceRepository,
    )

    svc: InvestigationService = service_env["service"]
    org_a: str = service_env["org_a"]
    crop_path: Path = service_env["crop_path"]

    subj = svc.create_authorized_subject(
        organization_id=org_a,
        full_name="Unrelated Error Subject",
        designation="Auditor",
        id_reference="EMP-ERR-01",
    )

    dto = SignatureReferenceEnrollDTO(
        organization_id=org_a,
        subject_id=subj.id,
        crop_image_path=str(crop_path),
        source_document_ref="Doc 1",
        consent_mandate_ref="Mandate 1",
        investigation_id="inv_nonexistent_000000000000000001",
    )

    # When uow.audit_events.add fails with foreign key violation (or mock error),
    # enroll_signature_reference must re-raise rather than returning an existing DTO
    with (
        patch.object(
            SqliteSignatureReferenceRepository,
            "add",
            side_effect=IntegrityError("FOREIGN KEY constraint failed", None, None),  # type: ignore[arg-type]
        ),
        pytest.raises(IntegrityError, match="FOREIGN KEY"),
    ):
        svc.enroll_signature_reference(dto)
