"""Integration tests for SqlAlchemyUnitOfWork transaction boundaries.

Verifies atomic commit across repositories, automatic rollback on unhandled exceptions,
manual rollback, session sharing, and proper connection cleanup.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.document import DocumentType
from veritrace.domain.enums.investigation import InvestigationStatus
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database path."""
    return tmp_path / "test_uow.sqlite"


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    """Fixture providing configured Alembic Config pointing to temp DB."""
    cfg = Config("alembic.ini")
    url = f"sqlite:///{db_path.as_posix()}"
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_unit_of_work_commit_persists_across_multiple_repositories(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify that multiple repository operations commit atomically on clean context exit."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    doc_id = "doc_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    aud_id = "aud_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id=org_id,
                name="Atomic Commit Enterprise",
                industry_sector="MANUFACTURING",
                created_at=now,
            )
            session.add(org)

        uow = SqlAlchemyUnitOfWork(session_factory)
        with uow:
            # 1. Add Investigation
            inv = Investigation(
                id=inv_id,
                organization_id=org_id,
                title="Atomic Case",
                reference_code="INV-UOW-01",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            uow.investigations.add(inv)

            # 2. Add Document via same transactional context
            doc = Document(
                id=doc_id,
                investigation_id=inv.id,
                original_filename="contract.pdf",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                mime_type="application/pdf",
                document_type=DocumentType.PURCHASE_ORDER,
                created_at=now,
            )
            uow.documents.add(doc, org_id)

            # 3. Append AuditEvent via same transactional context
            aud = AuditEvent(
                id=aud_id,
                investigation_id=inv.id,
                event_type=AuditEventType.CASE_CREATED,
                actor_type=ActorType.HUMAN_ANALYST,
                actor_id="analyst_uow",
                timestamp=now,
                event_payload={"action": "created_via_uow"},
            )
            uow.audit_events.add(aud, org_id)

        # Verify all changes persisted in fresh context
        with SqlAlchemyUnitOfWork(session_factory) as check_uow:
            persisted_inv = check_uow.investigations.get_by_id(inv_id, org_id)
            persisted_doc = check_uow.documents.get_by_id(doc_id, org_id)
            persisted_events = check_uow.audit_events.list_by_investigation(inv_id, org_id)
            assert persisted_inv is not None
            assert persisted_doc is not None
            assert len(persisted_events) == 1
            assert persisted_events[0].id == aud_id
    finally:
        engine.dispose()


def test_unit_of_work_rollback_on_exception_discards_all_changes(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify that unhandled exceptions inside with-block roll back all changes."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id=org_id,
                name="Rollback Test Org",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add(org)

        uow = SqlAlchemyUnitOfWork(session_factory)
        with pytest.raises(ValueError, match="Simulated pipeline failure"), uow:
            inv = Investigation(
                id=inv_id,
                organization_id=org_id,
                title="Failed Case",
                reference_code="INV-FAIL-01",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            uow.investigations.add(inv)

            # Simulated error mid-transaction
            raise ValueError("Simulated pipeline failure")

        # Verify that the investigation was rolled back and was NOT persisted
        with SqlAlchemyUnitOfWork(session_factory) as check_uow:
            retrieved = check_uow.investigations.get_by_id(inv_id, org_id)
            assert retrieved is None
    finally:
        engine.dispose()


def test_unit_of_work_manual_rollback(db_path: Path, alembic_config: Config) -> None:
    """Verify that calling uow.rollback() explicitly clears pending operations."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            org = OrganizationModel(
                id=org_id,
                name="Manual Rollback Corp",
                industry_sector="BFSI",
                created_at=now,
            )
            session.add(org)

        uow = SqlAlchemyUnitOfWork(session_factory)
        with uow:
            inv = Investigation(
                id=inv_id,
                organization_id=org_id,
                title="Manual Discard Case",
                reference_code="INV-MAN-01",
                status=InvestigationStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
            uow.investigations.add(inv)
            uow.rollback()

        with SqlAlchemyUnitOfWork(session_factory) as check_uow:
            assert check_uow.investigations.get_by_id(inv_id, org_id) is None
    finally:
        engine.dispose()


def test_unit_of_work_outside_context_raises_runtime_error(
    db_path: Path, alembic_config: Config
) -> None:
    """Verify accessing repositories outside with-block raises descriptive RuntimeError."""
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="UnitOfWork is not active"):
        _ = uow.investigations

    with pytest.raises(RuntimeError, match="UnitOfWork is not active"):
        _ = uow.documents

    with pytest.raises(RuntimeError, match="UnitOfWork is not active"):
        _ = uow.findings

    with pytest.raises(RuntimeError, match="UnitOfWork is not active"):
        _ = uow.evidence

    with pytest.raises(RuntimeError, match="UnitOfWork is not active"):
        _ = uow.audit_events

    with pytest.raises(RuntimeError, match="UnitOfWork is not active"):
        _ = uow.session
    engine.dispose()
