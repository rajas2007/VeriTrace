"""Integration tests for SQLite repository implementations with real database operations.

Verifies CRUD operations, mandatory tenant isolation across all queries,
evidence association linking/unlinking, append-only audit persistence,
and missing-record handling.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.document import DocumentStatus, DocumentType
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    ReviewDecisionType,
)
from veritrace.domain.enums.investigation import InvestigationStatus, RiskClassification
from veritrace.domain.exceptions.base import (
    EntityNotFoundError,
    RelationshipConstraintError,
    TenantIsolationError,
)
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.document_page import DocumentPageModel
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.models.review_decision import (
    ReviewDecisionModel,
)
from veritrace.infrastructure.persistence.repositories.audit_event_repository import (
    SqliteAuditEventRepository,
)
from veritrace.infrastructure.persistence.repositories.document_repository import (
    SqliteDocumentRepository,
)
from veritrace.infrastructure.persistence.repositories.evidence_repository import (
    SqliteEvidenceRepository,
)
from veritrace.infrastructure.persistence.repositories.finding_repository import (
    SqliteFindingRepository,
)
from veritrace.infrastructure.persistence.repositories.investigation_repository import (
    SqliteInvestigationRepository,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database path."""
    return tmp_path / "test_repos.sqlite"


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    """Fixture providing configured Alembic Config pointing to temp DB."""
    cfg = Config("alembic.ini")
    url = f"sqlite:///{db_path.as_posix()}"
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_investigation_repository_lifecycle(db_path: Path, alembic_config: Config) -> None:
    """Verify Investigation repository CRUD, pagination, and tenant isolation."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_a_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    org_b_id = "org_bbbbbbbbbbbbbbbbbbbbbbbbbbbb0001"
    inv1_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv2_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0002"

    try:
        # Seed Organizations A and B
        with session_scope(session_factory) as session:
            org_a = OrganizationModel(
                id=org_a_id,
                name="Alpha Steel Ltd",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            org_b = OrganizationModel(
                id=org_b_id,
                name="Beta Logistics Corp",
                industry_sector="LOGISTICS",
                created_at=now,
            )
            session.add_all([org_a, org_b])

        # 1. Create and add investigation for Org A
        with session_scope(session_factory) as session:
            repo = SqliteInvestigationRepository(session)
            inv1 = Investigation(
                id=inv1_id,
                organization_id=org_a_id,
                title="Q1 Alloy Inspection",
                reference_code="INV-ALPHA-001",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            inv2 = Investigation(
                id=inv2_id,
                organization_id=org_a_id,
                title="Q2 Valve Inspection",
                reference_code="INV-ALPHA-002",
                status=InvestigationStatus.PROCESSING,
                created_at=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
            )
            repo.add(inv1)
            repo.add(inv2)

        # 2. Retrieve by ID scoped to Org A (found) vs Org B (not found)
        with session_scope(session_factory) as session:
            repo = SqliteInvestigationRepository(session)
            retrieved = repo.get_by_id(inv1_id, org_a_id)
            assert retrieved is not None
            assert retrieved.title == "Q1 Alloy Inspection"

            # Tenant isolation: Org B cannot see Org A's case
            cross_retrieved = repo.get_by_id(inv1_id, org_b_id)
            assert cross_retrieved is None

        # 3. Retrieve by reference code
        with session_scope(session_factory) as session:
            repo = SqliteInvestigationRepository(session)
            by_ref = repo.get_by_reference_code("INV-ALPHA-001", org_a_id)
            assert by_ref is not None
            assert by_ref.id == inv1_id

            by_ref_cross = repo.get_by_reference_code("INV-ALPHA-001", org_b_id)
            assert by_ref_cross is None

        # 4. List by organization with pagination
        with session_scope(session_factory) as session:
            repo = SqliteInvestigationRepository(session)
            all_alpha = repo.list_by_organization(org_a_id)
            assert len(all_alpha) == 2
            assert all_alpha[0].id == inv2_id  # desc order

            paged_alpha = repo.list_by_organization(org_a_id, skip=1, limit=1)
            assert len(paged_alpha) == 1
            assert paged_alpha[0].id == inv1_id

            beta_list = repo.list_by_organization(org_b_id)
            assert len(beta_list) == 0

        # 5. Update investigation status and risk score
        with session_scope(session_factory) as session:
            repo = SqliteInvestigationRepository(session)
            inv1_updated = Investigation(
                id=inv1_id,
                organization_id=org_a_id,
                title="Q1 Alloy Inspection - Escalated",
                reference_code="INV-ALPHA-001",
                status=InvestigationStatus.COMPLETED,
                risk_score=0.95,
                risk_classification=RiskClassification.SUSPECTED_MANIPULATION,
                created_at=now,
                updated_at=datetime(2026, 1, 3, 10, 0, 0, tzinfo=UTC),
            )
            repo.update(inv1_updated, org_a_id)

        with session_scope(session_factory) as session:
            repo = SqliteInvestigationRepository(session)
            check_updated = repo.get_by_id(inv1_id, org_a_id)
            assert check_updated is not None
            assert check_updated.title == "Q1 Alloy Inspection - Escalated"
            assert check_updated.status == InvestigationStatus.COMPLETED
            assert check_updated.risk_score == 0.95

            # Attempting update with mismatched organization raises TenantIsolationError
            with pytest.raises(TenantIsolationError, match="Cross-organization access violation"):
                repo.update(inv1_updated, org_b_id)

            # Updating non-existent entity raises EntityNotFoundError
            non_existent = Investigation(
                id="inv_00000000000000000000000000000099",
                organization_id=org_a_id,
                title="Ghost Case",
                reference_code="INV-GHOST-01",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            with pytest.raises(EntityNotFoundError, match="not found in organization"):
                repo.update(non_existent, org_a_id)
    finally:
        engine.dispose()


def test_document_repository_lifecycle_and_tenant_isolation(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify Document repository CRUD, duplicate hash lookup, and tenant scoping."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_a_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    org_b_id = "org_bbbbbbbbbbbbbbbbbbbbbbbbbbbb0001"
    inv_a_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    doc_id = "doc_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            org_a = OrganizationModel(
                id=org_a_id,
                name="Org A Doc Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            org_b = OrganizationModel(
                id=org_b_id,
                name="Org B Doc Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            inv_a = Investigation(
                id=inv_a_id,
                organization_id=org_a_id,
                title="Case A",
                reference_code="INV-DOC-A",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            session.add_all([org_a, org_b])
            SqliteInvestigationRepository(session).add(inv_a)

        # 1. Add document under Inv A with Org A
        doc = Document(
            id=doc_id,
            investigation_id=inv_a_id,
            original_filename="invoice_2026.pdf",
            file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            mime_type="application/pdf",
            document_type=DocumentType.COMMERCIAL_INVOICE,
            created_at=now,
        )

        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            repo.add(doc, org_a_id)

        # 2. Attempting to add document claiming Org B raises TenantIsolationError
        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            doc_invalid_org = Document(
                id="doc_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0002",
                investigation_id=inv_a_id,
                original_filename="cross_leak.pdf",
                file_hash_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                mime_type="application/pdf",
                document_type=DocumentType.COMMERCIAL_INVOICE,
                created_at=now,
            )
            with pytest.raises(TenantIsolationError, match="Cross-organization violation"):
                repo.add(doc_invalid_org, org_b_id)

        # 3. Retrieve by ID scoped to Org A vs Org B
        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            retrieved = repo.get_by_id(doc_id, org_a_id)
            assert retrieved is not None
            assert retrieved.original_filename == "invoice_2026.pdf"

            # Scoped to Org B must return None
            assert repo.get_by_id(doc_id, org_b_id) is None

        # 4. Hash lookup scoped to tenant
        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            matches_a = repo.get_by_hash(
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                org_a_id,
            )
            assert len(matches_a) == 1
            assert matches_a[0].id == doc_id

            matches_b = repo.get_by_hash(
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                org_b_id,
            )
            assert len(matches_b) == 0

        # 5. List by investigation scoped to tenant
        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            docs = repo.list_by_investigation(inv_a_id, org_a_id)
            assert len(docs) == 1

            # Org B querying Inv A raises TenantIsolationError
            with pytest.raises(TenantIsolationError, match="Cross-organization violation"):
                repo.list_by_investigation(inv_a_id, org_b_id)

        # 6. Update document
        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            updated_doc = Document(
                id=doc_id,
                investigation_id=inv_a_id,
                original_filename="invoice_2026.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                document_type=DocumentType.COMMERCIAL_INVOICE,
                created_at=now,
                status=DocumentStatus.PROCESSED,
            )
            repo.update(updated_doc, org_a_id)

            with pytest.raises(TenantIsolationError, match="Cross-organization access violation"):
                repo.update(updated_doc, org_b_id)

        with session_scope(session_factory) as session:
            repo = SqliteDocumentRepository(session)
            res = repo.get_by_id(doc_id, org_a_id)
            assert res is not None
            assert res.status == DocumentStatus.PROCESSED
    finally:
        engine.dispose()


def test_finding_repository_lifecycle_and_evidence_linking(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify Finding repository CRUD, evidence association sync, and delete guards."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    doc_id = "doc_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    page_id = "page_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    ev1_id = "evd_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    ev2_id = "evd_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0002"
    fnd_id = "fnd_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id=org_id,
                name="Finding Test Corp",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            inv = Investigation(
                id=inv_id,
                organization_id=org_id,
                title="Finding Case",
                reference_code="INV-FND-01",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            doc = Document(
                id=doc_id,
                investigation_id=inv_id,
                original_filename="sample.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                document_type=DocumentType.COMMERCIAL_INVOICE,
                created_at=now,
            )
            session.add(org)
            SqliteInvestigationRepository(session).add(inv)
            SqliteDocumentRepository(session).add(doc, org_id)

            page = DocumentPageModel(
                id=page_id,
                document_id=doc_id,
                page_number=1,
                width_pixels=1000,
                height_pixels=1000,
                image_storage_path="pages/p1.png",
            )
            session.add(page)
            session.flush()

            ev1 = Evidence(
                id=ev1_id,
                page_id=page_id,
                crop_image_path="crops/crop1.png",
                normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.3),
            )
            ev2 = Evidence(
                id=ev2_id,
                page_id=page_id,
                crop_image_path="crops/crop2.png",
                normalized_bbox=NormalizedBoundingBox(ymin=0.4, xmin=0.4, ymax=0.6, xmax=0.6),
            )
            SqliteEvidenceRepository(session).add(ev1, org_id)
            SqliteEvidenceRepository(session).add(ev2, org_id)

        # 1. Add finding with linked evidence items
        finding = Finding(
            id=fnd_id,
            investigation_id=inv_id,
            category=FindingCategory.COPY_MOVE_CLONE,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.HIGH,
            title="Duplicate Date Stamp",
            narrative_explanation="Identical raster patterns at two distinct regions",
            created_at=now,
            _evidence_ids={ev1_id, ev2_id},
        )

        with session_scope(session_factory) as session:
            repo = SqliteFindingRepository(session)
            repo.add(finding, org_id)

        # 2. Retrieve finding and verify evidence links
        with session_scope(session_factory) as session:
            repo = SqliteFindingRepository(session)
            retrieved = repo.get_by_id(fnd_id, org_id)
            assert retrieved is not None
            assert retrieved.evidence_ids == {ev1_id, ev2_id}

        # 3. Unlink evidence via update
        finding.unlink_evidence(ev2_id)
        with session_scope(session_factory) as session:
            repo = SqliteFindingRepository(session)
            repo.update(finding, org_id)

        with session_scope(session_factory) as session:
            repo = SqliteFindingRepository(session)
            retrieved_after_unlink = repo.get_by_id(fnd_id, org_id)
            assert retrieved_after_unlink is not None
            assert retrieved_after_unlink.evidence_ids == {ev1_id}

            # Verify unlinked evidence entity still exists in persistence
            ev_repo = SqliteEvidenceRepository(session)
            ev2_check = ev_repo.get_by_id(ev2_id, org_id)
            assert ev2_check is not None

        # 4. Attach ReviewDecision and verify delete is blocked
        with session_scope(session_factory) as session:
            rev = ReviewDecisionModel(
                id="rev_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001",
                finding_id=fnd_id,
                reviewer_id="human_examiner",
                decision=ReviewDecisionType.CONFIRMED.value,
                rationale="Manual review verified stroke discrepancy",
                timestamp=now,
            )
            session.add(rev)

        with session_scope(session_factory) as session:
            repo = SqliteFindingRepository(session)
            with pytest.raises(RelationshipConstraintError, match="protected by 1 recorded"):
                repo.delete(fnd_id, org_id)
    finally:
        engine.dispose()


def test_evidence_repository_lifecycle_and_tenant_isolation(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify Evidence repository queries and strict tenant boundary validation."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_a_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    org_b_id = "org_bbbbbbbbbbbbbbbbbbbbbbbbbbbb0001"
    inv_a_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    doc_a_id = "doc_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    page_id = "page_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    ev_id = "evd_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            org_a = OrganizationModel(
                id=org_a_id,
                name="Evidence A Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            org_b = OrganizationModel(
                id=org_b_id,
                name="Evidence B Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            inv_a = Investigation(
                id=inv_a_id,
                organization_id=org_a_id,
                title="Case A",
                reference_code="INV-EV-A",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            doc_a = Document(
                id=doc_a_id,
                investigation_id=inv_a_id,
                original_filename="doc_a.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                document_type=DocumentType.COMMERCIAL_INVOICE,
                created_at=now,
            )
            session.add_all([org_a, org_b])
            SqliteInvestigationRepository(session).add(inv_a)
            SqliteDocumentRepository(session).add(doc_a, org_a_id)

            page = DocumentPageModel(
                id=page_id,
                document_id=doc_a_id,
                page_number=1,
                width_pixels=2000,
                height_pixels=3000,
                image_storage_path="pages/doc_a_p1.png",
            )
            session.add(page)
            session.flush()

        # 1. Add evidence
        ev = Evidence(
            id=ev_id,
            page_id=page_id,
            crop_image_path="crops/seal.png",
            normalized_bbox=NormalizedBoundingBox(ymin=0.2, xmin=0.2, ymax=0.4, xmax=0.4),
        )

        with session_scope(session_factory) as session:
            repo = SqliteEvidenceRepository(session)
            repo.add(ev, org_a_id)

            # Attempting add with Org B raises TenantIsolationError
            with pytest.raises(TenantIsolationError, match="Cross-organization violation"):
                repo.add(ev, org_b_id)

        # 2. Scoped retrieval by ID
        with session_scope(session_factory) as session:
            repo = SqliteEvidenceRepository(session)
            res_a = repo.get_by_id(ev_id, org_a_id)
            assert res_a is not None
            assert res_a.crop_image_path == "crops/seal.png"

            # Scoped to Org B must return None
            assert repo.get_by_id(ev_id, org_b_id) is None

        # 3. List by page and list by investigation
        with session_scope(session_factory) as session:
            repo = SqliteEvidenceRepository(session)
            page_items = repo.list_by_page(page_id, org_a_id)
            assert len(page_items) == 1

            inv_items = repo.list_by_investigation(inv_a_id, org_a_id)
            assert len(inv_items) == 1

            # Cross-tenant listing raises TenantIsolationError
            with pytest.raises(TenantIsolationError, match="Cross-organization violation"):
                repo.list_by_page(page_id, org_b_id)
            with pytest.raises(TenantIsolationError, match="Cross-organization violation"):
                repo.list_by_investigation(inv_a_id, org_b_id)
    finally:
        engine.dispose()


def test_audit_event_repository_append_only_and_chronology(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify AuditEvent repository append-only behavior, deterministic chronological sorting."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 10, 5, 0, tzinfo=UTC)
    t3 = datetime(2026, 1, 1, 10, 10, 0, tzinfo=UTC)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    e1_id = "aud_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    e2_id = "aud_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0002"
    e3_id = "aud_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0003"

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id=org_id,
                name="Audit Org",
                industry_sector="BFSI",
                created_at=t1,
            )
            inv = Investigation(
                id=inv_id,
                organization_id=org_id,
                title="Audit Track Case",
                reference_code="INV-AUD-TRK",
                status=InvestigationStatus.DRAFT,
                created_at=t1,
                updated_at=t1,
            )
            session.add(org)
            SqliteInvestigationRepository(session).add(inv)

        # 1. Append chronological events
        e1 = AuditEvent(
            id=e1_id,
            investigation_id=inv_id,
            event_type=AuditEventType.CASE_CREATED,
            actor_type=ActorType.SYSTEM_PIPELINE,
            actor_id="system",
            timestamp=t1,
            event_payload={"step": "init"},
        )
        e2 = AuditEvent(
            id=e2_id,
            investigation_id=inv_id,
            event_type=AuditEventType.DOC_UPLOADED,
            actor_type=ActorType.HUMAN_ANALYST,
            actor_id="user_01",
            timestamp=t2,
            event_payload={"file": "doc.pdf"},
        )
        e3 = AuditEvent(
            id=e3_id,
            investigation_id=inv_id,
            event_type=AuditEventType.HUMAN_REVIEW_CONFIRMED,
            actor_type=ActorType.HUMAN_ANALYST,
            actor_id="user_01",
            timestamp=t3,
            event_payload={"finding": "confirmed"},
        )

        with session_scope(session_factory) as session:
            repo = SqliteAuditEventRepository(session)
            repo.add(e1, org_id)
            repo.add(e2, org_id)
            repo.add(e3, org_id)

        # 2. Verify chronological query order
        with session_scope(session_factory) as session:
            repo = SqliteAuditEventRepository(session)
            events = repo.list_by_investigation(inv_id, org_id)
            assert len(events) == 3
            assert [e.id for e in events] == [e1_id, e2_id, e3_id]
            assert events[0].timestamp < events[1].timestamp < events[2].timestamp

        # 3. Verify protocol invariant: no update/delete methods exist
        repo_instance = SqliteAuditEventRepository(session)
        assert not hasattr(repo_instance, "update")
        assert not hasattr(repo_instance, "delete")
    finally:
        engine.dispose()
