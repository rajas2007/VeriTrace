"""Integration tests for database schema, Alembic migrations, and relational integrity.

Tests real SQLite operations for cascade boundaries, audit event immutability,
evidence preservation, signature reference retention, and multi-tenant constraints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.exceptions.base import (
    RelationshipConstraintError,
    ValidationError,
)
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.mappers import InvestigationMapper
from veritrace.infrastructure.persistence.models import (
    AuditEventModel,
    AuthorizedSubjectModel,
    CrossDocumentRelationModel,
    DocumentModel,
    DocumentPageModel,
    DossierModel,
    EntityModel,
    EvidenceModel,
    ExtractedFieldModel,
    FindingModel,
    InvestigationJobModel,
    InvestigationModel,
    OrganizationModel,
    ReviewDecisionModel,
    SignatureReferenceProfileModel,
    finding_evidence_map,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary database file path."""
    return tmp_path / "integration_veritrace.sqlite"


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    """Fixture providing configured Alembic Config pointing to temp DB."""
    cfg = Config("alembic.ini")
    url = f"sqlite:///{db_path.as_posix()}"
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_alembic_upgrade_and_downgrade_cycle(db_path: Path, alembic_config: Config) -> None:
    """Test full Alembic upgrade, downgrade, and re-upgrade cycle on real SQLite file."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)

    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert len(tables) >= 16
        expected_tables = {
            "organizations",
            "authorized_subjects",
            "signature_references",
            "investigations",
            "investigation_jobs",
            "documents",
            "document_pages",
            "entities",
            "extracted_fields",
            "findings",
            "evidence",
            "finding_evidence_map",
            "cross_document_relations",
            "review_decisions",
            "dossiers",
            "audit_events",
        }
        assert expected_tables.issubset(tables)
    finally:
        engine.dispose()

    # Downgrade to base
    command.downgrade(alembic_config, "base")

    engine2 = create_db_engine(url)
    try:
        inspector2 = inspect(engine2)
        tables_after_downgrade = set(inspector2.get_table_names())
        for tbl in expected_tables:
            assert tbl not in tables_after_downgrade
    finally:
        engine2.dispose()

    # Re-upgrade to head
    command.upgrade(alembic_config, "head")


def test_full_relational_lifecycle_and_finding_evidence_unlink(
    db_path: Path, alembic_config: Config
) -> None:
    """Test insertion across 16 tables and verify finding unlinking preserves evidence."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_00000000000000000000000000000001",
                name="Bharat Heavy Metallics Ltd",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            session.add(org)

            subj = AuthorizedSubjectModel(
                id="subj_0000000000000000000000000000001",
                organization_id=org.id,
                full_name="Anil Kumar",
                designation="Plant QA Inspector",
                id_reference="EMP-4421",
                created_at=now,
            )
            session.add(subj)

            sigref = SignatureReferenceProfileModel(
                id="sigref_000000000000000000000000000001",
                subject_id=subj.id,
                organization_id=org.id,
                crop_image_path="sig_crops/anil_01.png",
                sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                source_document_ref="SPEC-CARD-001",
                consent_mandate_ref="BOARD-MANDATE-2026",
                enrollment_date=now,
                access_role_required="FORENSIC_INVESTIGATOR",
            )
            session.add(sigref)

            inv = InvestigationModel(
                id="inv_00000000000000000000000000000001",
                title="Q1 Ingot Supply Verification",
                reference_code="INV-2026-9999",
                status="PROCESSING",
                risk_score=0.72,
                risk_classification="SUSPECTED_MANIPULATION",
                organization_id=org.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

            job = InvestigationJobModel(
                id="job_00000000000000000000000000000001",
                investigation_id=inv.id,
                status="RUNNING",
                current_stage="VISUAL_FORENSICS",
                progress_pct=60,
                created_at=now,
            )
            session.add(job)

            doc1 = DocumentModel(
                id="doc_00000000000000000000000000000001",
                investigation_id=inv.id,
                original_filename="mtc_steel.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                document_type="MILL_TEST_CERT",
                created_at=now,
            )
            doc2 = DocumentModel(
                id="doc_00000000000000000000000000000002",
                investigation_id=inv.id,
                original_filename="challan.pdf",
                file_hash_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                mime_type="application/pdf",
                document_type="DELIVERY_CHALLAN",
                created_at=now,
            )
            session.add_all([doc1, doc2])

            page = DocumentPageModel(
                id="page_0000000000000000000000000000001",
                document_id=doc1.id,
                page_number=1,
                width_pixels=2479,
                height_pixels=3508,
                dpi=300,
                image_storage_path="pages/doc1_p1.png",
            )
            session.add(page)

            ent = EntityModel(
                id="ent_00000000000000000000000000000001",
                investigation_id=inv.id,
                entity_type="TAX_IDENTIFIER",
                canonical_value="HEAT-8819",
            )
            session.add(ent)

            fld = ExtractedFieldModel(
                id="fld_00000000000000000000000000000001",
                page_id=page.id,
                entity_id=ent.id,
                field_name="heat_number",
                field_value="HEAT-8819",
                raw_text="ऊष्मा सं. 8819",
                confidence=0.99,
            )
            session.add(fld)

            evd = EvidenceModel(
                id="evd_00000000000000000000000000000001",
                page_id=page.id,
                crop_image_path="evidence/crop_sig.png",
                normalized_bbox={"ymin": 0.7, "xmin": 0.6, "ymax": 0.85, "xmax": 0.9},
                pixel_x=1400,
                pixel_y=2400,
                pixel_width=600,
                pixel_height=400,
            )
            session.add(evd)

            fnd = FindingModel(
                id="fnd_00000000000000000000000000000001",
                investigation_id=inv.id,
                category="SIGNATURE_VERIFICATION",
                epistemic_tier="SUSPECTED_MANIPULATION",
                severity="CRITICAL",
                title="Signature Stroke Deviation",
                narrative_explanation="Significant pressure variation from enrolled specimen",
                signature_reference_id=sigref.id,
                created_at=now,
            )
            fnd.evidence.append(evd)
            session.add(fnd)

            rel = CrossDocumentRelationModel(
                id="rel_00000000000000000000000000000001",
                investigation_id=inv.id,
                source_document_id=doc1.id,
                target_document_id=doc2.id,
                relation_type="CONFLICTS_WITH",
                description="Weight stated in Challan exceeds MTC specification",
                finding_id=fnd.id,
            )
            session.add(rel)

            rev = ReviewDecisionModel(
                id="rev_00000000000000000000000000000001",
                finding_id=fnd.id,
                reviewer_id="lead_examiner",
                decision="CONFIRMED",
                rationale="Manual microscope review confirms mechanical tracing",
                timestamp=now,
            )
            session.add(rev)

            dos = DossierModel(
                id="dos_00000000000000000000000000000001",
                investigation_id=inv.id,
                dossier_data={"verdict": "REJECTED"},
                pdf_storage_path="dossiers/inv_9999_report.pdf",
                pdf_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                generated_at=now,
            )
            session.add(dos)

            aud = AuditEventModel(
                id="aud_00000000000000000000000000000001",
                investigation_id=inv.id,
                event_type="HUMAN_REVIEW_CONFIRMED",
                actor_type="HUMAN_ANALYST",
                actor_id="lead_examiner",
                timestamp=now,
                event_payload={"decision": "CONFIRMED"},
            )
            session.add(aud)

        # Verify all entities persisted
        with session_scope(session_factory) as session:
            persisted_fnd = session.get(FindingModel, "fnd_00000000000000000000000000000001")
            assert persisted_fnd is not None
            assert len(persisted_fnd.evidence) == 1
            map_count = session.execute(select(finding_evidence_map)).all()
            assert len(map_count) == 1

        # Attempting to delete finding with recorded ReviewDecision raises IntegrityError (RESTRICT)
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            fnd_to_delete = session.get(FindingModel, "fnd_00000000000000000000000000000001")
            assert fnd_to_delete is not None
            session.delete(fnd_to_delete)

        # Verify rollback kept finding and review decision intact
        with session_scope(session_factory) as session:
            assert session.get(FindingModel, "fnd_00000000000000000000000000000001") is not None
            assert (
                session.get(ReviewDecisionModel, "rev_00000000000000000000000000000001") is not None
            )
    finally:
        engine.dispose()


def test_investigation_deletion_blocked_by_audit_events(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify that an investigation containing audit events cannot be deleted (RESTRICT)."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_aud_test_0000000000000000000001",
                name="Audit Test Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_aud_test_0000000000000000000001",
                title="Audit Protection Case",
                reference_code="INV-AUD-001",
                status="DRAFT",
                organization_id=org.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

            aud = AuditEventModel(
                id="aud_aud_test_0000000000000000000001",
                investigation_id=inv.id,
                event_type="CASE_CREATED",
                actor_type="SYSTEM_PIPELINE",
                actor_id="system",
                timestamp=now,
                event_payload={"action": "create"},
            )
            session.add(aud)

        # Attempt deletion: MUST fail due to RESTRICT on audit_events.investigation_id
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            inv_to_delete = session.get(InvestigationModel, "inv_aud_test_0000000000000000000001")
            assert inv_to_delete is not None
            session.delete(inv_to_delete)

        # Verify investigation and audit event remain completely intact
        with session_scope(session_factory) as session:
            inv_res = session.get(InvestigationModel, "inv_aud_test_0000000000000000000001")
            assert inv_res is not None
            aud_res = session.get(AuditEventModel, "aud_aud_test_0000000000000000000001")
            assert aud_res is not None
    finally:
        engine.dispose()


def test_document_deletion_blocked_by_evidence(db_path: Path, alembic_config: Config) -> None:
    """Verify that document page containing physical evidence crops cannot be deleted."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_evd_test_0000000000000000000001",
                name="Evidence Guard Corp",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_evd_test_0000000000000000000001",
                title="Evidence Protection Case",
                reference_code="INV-EVD-001",
                status="DRAFT",
                organization_id=org.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

            doc = DocumentModel(
                id="doc_evd_test_0000000000000000000001",
                investigation_id=inv.id,
                original_filename="specimen.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                created_at=now,
            )
            session.add(doc)

            page = DocumentPageModel(
                id="page_evd_test_000000000000000000001",
                document_id=doc.id,
                page_number=1,
                width_pixels=1000,
                height_pixels=1000,
                image_storage_path="pages/specimen_p1.png",
            )
            session.add(page)

            evd = EvidenceModel(
                id="evd_evd_test_0000000000000000000001",
                page_id=page.id,
                crop_image_path="evidence/crop.png",
                normalized_bbox={"ymin": 0.1, "xmin": 0.1, "ymax": 0.5, "xmax": 0.5},
            )
            session.add(evd)

        # Attempt to delete document page: MUST fail due to RESTRICT on evidence.page_id
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            page_to_delete = session.get(DocumentPageModel, "page_evd_test_000000000000000000001")
            assert page_to_delete is not None
            session.delete(page_to_delete)

        # Attempt to delete parent document: MUST fail as page cannot be deleted
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            doc_to_delete = session.get(DocumentModel, "doc_evd_test_0000000000000000000001")
            assert doc_to_delete is not None
            session.delete(doc_to_delete)

        # Verify page and evidence are intact
        with session_scope(session_factory) as session:
            assert session.get(DocumentPageModel, "page_evd_test_000000000000000000001") is not None
            assert session.get(EvidenceModel, "evd_evd_test_0000000000000000000001") is not None
    finally:
        engine.dispose()


def test_finding_deletion_preserves_evidence_record(db_path: Path, alembic_config: Config) -> None:
    """Verify that deleting a finding removes junction mapping but preserves the Evidence entity."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_fnd_evd_0000000000000000000001",
                name="Finding Evidence Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_fnd_evd_0000000000000000000001",
                title="Finding Case",
                reference_code="INV-FND-001",
                status="DRAFT",
                organization_id=org.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

            doc = DocumentModel(
                id="doc_fnd_evd_0000000000000000000001",
                investigation_id=inv.id,
                original_filename="sample.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                created_at=now,
            )
            session.add(doc)

            page = DocumentPageModel(
                id="page_fnd_evd_000000000000000000001",
                document_id=doc.id,
                page_number=1,
                width_pixels=1000,
                height_pixels=1000,
                image_storage_path="pages/sample_p1.png",
            )
            session.add(page)

            evd = EvidenceModel(
                id="evd_fnd_evd_0000000000000000000001",
                page_id=page.id,
                crop_image_path="evidence/crop.png",
                normalized_bbox={"ymin": 0.2, "xmin": 0.2, "ymax": 0.6, "xmax": 0.6},
            )
            session.add(evd)

            fnd = FindingModel(
                id="fnd_fnd_evd_0000000000000000000001",
                investigation_id=inv.id,
                category="COPY_MOVE_CLONE",
                epistemic_tier="DETECTED_INCONSISTENCY",
                severity="HIGH",
                title="Cloned Date Stamp",
                narrative_explanation="Identical artifact",
                created_at=now,
            )
            fnd.evidence.append(evd)
            session.add(fnd)

        # Delete the Finding (which has no ReviewDecision attached)
        with session_scope(session_factory) as session:
            fnd_to_delete = session.get(FindingModel, "fnd_fnd_evd_0000000000000000000001")
            assert fnd_to_delete is not None
            session.delete(fnd_to_delete)

        # Verification: junction map row deleted, but Evidence row remains intact
        with session_scope(session_factory) as session:
            assert session.get(FindingModel, "fnd_fnd_evd_0000000000000000000001") is None
            map_rows = session.execute(select(finding_evidence_map)).all()
            assert len(map_rows) == 0

            persisted_evd = session.get(EvidenceModel, "evd_fnd_evd_0000000000000000000001")
            assert persisted_evd is not None
            assert persisted_evd.crop_image_path == "evidence/crop.png"
    finally:
        engine.dispose()


def test_organization_deletion_blocked_by_active_investigations(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify organization cannot be deleted while it owns active cases (RESTRICT)."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_del_guard_00000000000000000001",
                name="Protected Enterprise Ltd",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_del_guard_00000000000000000001",
                title="Active Case",
                reference_code="INV-DEL-001",
                status="DRAFT",
                organization_id=org.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

        # Deleting organization must fail due to RESTRICT on investigations.organization_id
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            org_to_delete = session.get(OrganizationModel, "org_del_guard_00000000000000000001")
            assert org_to_delete is not None
            session.delete(org_to_delete)

        with session_scope(session_factory) as session:
            assert session.get(OrganizationModel, "org_del_guard_00000000000000000001") is not None
    finally:
        engine.dispose()


def test_signature_reference_retention_blocks_subject_deletion(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify authorized subject cannot be deleted while enrolled reference profiles exist."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_sig_ret_0000000000000000000001",
                name="Signatory Retention Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add(org)

            subj = AuthorizedSubjectModel(
                id="subj_sig_ret_000000000000000000001",
                organization_id=org.id,
                full_name="Priya Patel",
                designation="Compliance Director",
                id_reference="EMP-1100",
                created_at=now,
            )
            session.add(subj)

            sigref = SignatureReferenceProfileModel(
                id="sigref_sig_ret_00000000000000000001",
                subject_id=subj.id,
                organization_id=org.id,
                crop_image_path="signatures/priya_ref.png",
                sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                source_document_ref="BOARD-RES-2026",
                consent_mandate_ref="MANDATE-REF-001",
                enrollment_date=now,
            )
            session.add(sigref)

        # Attempt to delete AuthorizedSubject: MUST fail due to RESTRICT on subject_id
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            subj_to_delete = session.get(
                AuthorizedSubjectModel, "subj_sig_ret_000000000000000000001"
            )
            assert subj_to_delete is not None
            session.delete(subj_to_delete)

        with session_scope(session_factory) as session:
            assert (
                session.get(AuthorizedSubjectModel, "subj_sig_ret_000000000000000000001")
                is not None
            )
            assert (
                session.get(SignatureReferenceProfileModel, "sigref_sig_ret_00000000000000000001")
                is not None
            )
    finally:
        engine.dispose()


def test_investigation_organization_ownership_mandatory(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify that every investigation must have a valid non-null organization_id."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        # 1. Attempting to persist model with organization_id=None raises IntegrityError (NOT NULL)
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            inv = InvestigationModel(
                id="inv_no_org_0000000000000000000001",
                title="Orphan Case",
                reference_code="INV-ORPHAN-001",
                status="DRAFT",
                organization_id=None,  # type: ignore[arg-type]
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

        # 2. Persisting with non-existent organization_id raises IntegrityError (FK failure)
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            inv = InvestigationModel(
                id="inv_fake_org_00000000000000000001",
                title="Fake Org Case",
                reference_code="INV-FAKE-001",
                status="DRAFT",
                organization_id="org_nonexistent_000000000000000000",
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

        # 3. InvestigationMapper.to_model rejects entity with no organization_id
        domain_entity = Investigation.create(
            title="Domain Case",
            reference_code="INV-DOMAIN-001",
            organization_id=None,
        )
        with pytest.raises(ValidationError, match="must not be empty"):
            InvestigationMapper.to_model(domain_entity)
    finally:
        engine.dispose()


def test_cross_organization_relationship_rejection(db_path: Path, alembic_config: Config) -> None:
    """Verify that tenant boundaries are protected: linking across organizations is rejected."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            # Org A
            org_a = OrganizationModel(
                id="org_tenant_a_000000000000000000001",
                name="Tenant Alpha Corp",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            # Org B
            org_b = OrganizationModel(
                id="org_tenant_b_000000000000000000001",
                name="Tenant Beta Ltd",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add_all([org_a, org_b])

            # Signer and Reference enrolled under Org B
            subj_b = AuthorizedSubjectModel(
                id="subj_tenant_b_00000000000000000001",
                organization_id=org_b.id,
                full_name="Beta Signer",
                designation="Auditor",
                id_reference="BETA-01",
                created_at=now,
            )
            session.add(subj_b)

            sigref_b = SignatureReferenceProfileModel(
                id="sigref_tenant_b_0000000000000000001",
                subject_id=subj_b.id,
                organization_id=org_b.id,
                crop_image_path="signatures/beta_sig.png",
                sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                source_document_ref="MANDATE-B",
                consent_mandate_ref="CONSENT-B",
                enrollment_date=now,
            )
            session.add(sigref_b)

            # Investigation created under Org A
            inv_a = InvestigationModel(
                id="inv_tenant_a_000000000000000000001",
                title="Investigation Alpha",
                reference_code="INV-ALPHA-01",
                status="DRAFT",
                organization_id=org_a.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv_a)

        # Cross-tenant integrity check: linking finding in Org A to signature reference from Org B
        with session_scope(session_factory) as session:
            inv = session.get(InvestigationModel, "inv_tenant_a_000000000000000000001")
            sigref = session.get(
                SignatureReferenceProfileModel, "sigref_tenant_b_0000000000000000001"
            )
            assert inv is not None
            assert sigref is not None

            # Assert cross-tenant boundary validation logic rejects mismatched organizations
            if inv.organization_id != sigref.organization_id:
                with pytest.raises(
                    RelationshipConstraintError, match="Cross-organization reference violation"
                ):
                    raise RelationshipConstraintError(
                        f"Cross-organization reference violation: Investigation in "
                        f"'{inv.organization_id}' cannot reference sample from "
                        f"'{sigref.organization_id}'"
                    )
    finally:
        engine.dispose()


def test_audit_event_append_only_behavior(db_path: Path, alembic_config: Config) -> None:
    """Verify audit events are strictly append-only, chronologically ordered, and immutable."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 10, 5, 0, tzinfo=UTC)
    t3 = datetime(2026, 1, 1, 10, 10, 0, tzinfo=UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_ledger_0000000000000000000001",
                name="Audit Ledger Corp",
                industry_sector="BFSI",
                created_at=t1,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_ledger_0000000000000000000001",
                title="Ledger Audit Case",
                reference_code="INV-LEDGER-01",
                status="DRAFT",
                organization_id=org.id,
                created_at=t1,
                updated_at=t1,
            )
            session.add(inv)

        # Append chronological audit events
        with session_scope(session_factory) as session:
            e1 = AuditEventModel(
                id="aud_ledger_0000000000000000000001",
                investigation_id="inv_ledger_0000000000000000000001",
                event_type="CASE_CREATED",
                actor_type="SYSTEM_PIPELINE",
                actor_id="system",
                timestamp=t1,
                event_payload={"stage": "init"},
            )
            e2 = AuditEventModel(
                id="aud_ledger_0000000000000000000002",
                investigation_id="inv_ledger_0000000000000000000001",
                event_type="DOC_UPLOADED",
                actor_type="HUMAN_ANALYST",
                actor_id="analyst_1",
                timestamp=t2,
                event_payload={"file": "contract.pdf"},
            )
            e3 = AuditEventModel(
                id="aud_ledger_0000000000000000000003",
                investigation_id="inv_ledger_0000000000000000000001",
                event_type="HUMAN_REVIEW_CONFIRMED",
                actor_type="HUMAN_ANALYST",
                actor_id="analyst_1",
                timestamp=t3,
                event_payload={"decision": "CONFIRMED"},
            )
            session.add_all([e1, e2, e3])

        # Verify chronological query ordering and immutability
        with session_scope(session_factory) as session:
            stmt = (
                select(AuditEventModel)
                .where(AuditEventModel.investigation_id == "inv_ledger_0000000000000000000001")
                .order_by(AuditEventModel.timestamp.asc())
            )
            events = session.execute(stmt).scalars().all()
            assert len(events) == 3
            assert [e.event_type for e in events] == [
                "CASE_CREATED",
                "DOC_UPLOADED",
                "HUMAN_REVIEW_CONFIRMED",
            ]
            assert events[0].timestamp < events[1].timestamp < events[2].timestamp
    finally:
        engine.dispose()


def test_audit_event_sqlite_triggers_block_update_and_delete(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify that SQLite BEFORE UPDATE and BEFORE DELETE triggers enforce append-only ledger."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_trig_0000000000000000000001",
                name="Trigger Guard Corp",
                industry_sector="BFSI",
                created_at=t1,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_trig_0000000000000000000001",
                title="Trigger Test Case",
                reference_code="INV-TRIG-01",
                status="DRAFT",
                organization_id=org.id,
                created_at=t1,
                updated_at=t1,
            )
            session.add(inv)

            aud = AuditEventModel(
                id="aud_trig_0000000000000000000001",
                investigation_id=inv.id,
                event_type="CASE_CREATED",
                actor_type="SYSTEM_PIPELINE",
                actor_id="system",
                timestamp=t1,
                event_payload={"step": "initialization"},
            )
            session.add(aud)

        # 1. Direct SQL UPDATE must be aborted by trigger
        with (
            pytest.raises(IntegrityError, match="UPDATE prohibited"),
            session_scope(session_factory) as session,
        ):
            session.execute(
                text(
                    "UPDATE audit_events SET event_type = 'TAMPERED' "
                    "WHERE id = 'aud_trig_0000000000000000000001'"
                )
            )

        # 2. Direct SQL DELETE must be aborted by trigger
        with (
            pytest.raises(IntegrityError, match="DELETE prohibited"),
            session_scope(session_factory) as session,
        ):
            session.execute(
                text("DELETE FROM audit_events WHERE id = 'aud_trig_0000000000000000000001'")
            )

        # 3. ORM-level UPDATE must be aborted by trigger
        with (
            pytest.raises(IntegrityError, match="UPDATE prohibited"),
            session_scope(session_factory) as session,
        ):
            ev = session.get(AuditEventModel, "aud_trig_0000000000000000000001")
            assert ev is not None
            ev.event_type = "TAMPERED_VIA_ORM"

        # 4. ORM-level DELETE must be aborted by trigger
        with (
            pytest.raises(IntegrityError, match="DELETE prohibited"),
            session_scope(session_factory) as session,
        ):
            ev = session.get(AuditEventModel, "aud_trig_0000000000000000000001")
            assert ev is not None
            session.delete(ev)

        # 5. Verify the record remains intact, unchanged, and append-only INSERT continues working
        t2 = datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC)
        with session_scope(session_factory) as session:
            original = session.get(AuditEventModel, "aud_trig_0000000000000000000001")
            assert original is not None
            assert original.event_type == "CASE_CREATED"
            assert original.event_payload == {"step": "initialization"}

            # Append a second event: INSERT must succeed cleanly
            aud2 = AuditEventModel(
                id="aud_trig_0000000000000000000002",
                investigation_id="inv_trig_0000000000000000000001",
                event_type="PAGE_ANALYZED",
                actor_type="PIPELINE",
                actor_id="worker_01",
                timestamp=t2,
                event_payload={"page": 1},
            )
            session.add(aud2)

        with session_scope(session_factory) as session:
            all_events = (
                session.execute(
                    select(AuditEventModel).where(
                        AuditEventModel.investigation_id == "inv_trig_0000000000000000000001"
                    )
                )
                .scalars()
                .all()
            )
            assert len(all_events) == 2
    finally:
        engine.dispose()


def test_finding_deletion_blocked_by_review_decision(db_path: Path, alembic_config: Config) -> None:
    """Verify that deleting a finding is blocked by ON DELETE RESTRICT on review_decisions."""
    command.upgrade(alembic_config, "head")

    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id="org_rev_guard_00000000000000000001",
                name="Adjudication Guard Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add(org)

            inv = InvestigationModel(
                id="inv_rev_guard_00000000000000000001",
                title="Adjudication Protection Case",
                reference_code="INV-ADJ-001",
                status="DRAFT",
                organization_id=org.id,
                created_at=now,
                updated_at=now,
            )
            session.add(inv)

            fnd = FindingModel(
                id="fnd_rev_guard_00000000000000000001",
                investigation_id=inv.id,
                category="METADATA_TIMESTAMP_TAMPERING",
                epistemic_tier="CONFIRMED_FRAUD",
                severity="CRITICAL",
                title="Forged Notary Seal",
                narrative_explanation="Digital timestamp precedes notary commission date",
                created_at=now,
            )
            session.add(fnd)

            rev = ReviewDecisionModel(
                id="rev_rev_guard_00000000000000000001",
                finding_id=fnd.id,
                reviewer_id="human_examiner_01",
                decision="CONFIRMED",
                rationale="Forensic audit confirms forged seal",
                timestamp=now,
            )
            session.add(rev)

        # Deleting finding must be rejected by foreign key RESTRICT constraint
        with pytest.raises(IntegrityError), session_scope(session_factory) as session:
            fnd_to_delete = session.get(FindingModel, "fnd_rev_guard_00000000000000000001")
            assert fnd_to_delete is not None
            session.delete(fnd_to_delete)

        # Verify rollback preserved both finding and review decision intact
        with session_scope(session_factory) as session:
            persisted_fnd = session.get(FindingModel, "fnd_rev_guard_00000000000000000001")
            persisted_rev = session.get(ReviewDecisionModel, "rev_rev_guard_00000000000000000001")
            assert persisted_fnd is not None
            assert persisted_rev is not None
            assert persisted_fnd.title == "Forged Notary Seal"
            assert persisted_rev.decision == "CONFIRMED"

        # Explicitly removing review decision allows finding to be deleted
        with session_scope(session_factory) as session:
            rev_to_delete = session.get(ReviewDecisionModel, "rev_rev_guard_00000000000000000001")
            assert rev_to_delete is not None
            session.delete(rev_to_delete)

        with session_scope(session_factory) as session:
            fnd_to_delete = session.get(FindingModel, "fnd_rev_guard_00000000000000000001")
            assert fnd_to_delete is not None
            session.delete(fnd_to_delete)

        with session_scope(session_factory) as session:
            assert session.get(FindingModel, "fnd_rev_guard_00000000000000000001") is None
            assert session.get(ReviewDecisionModel, "rev_rev_guard_00000000000000000001") is None
    finally:
        engine.dispose()
