"""Unit tests for InvestigationService."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError as PydanticValidationError

from veritrace.application.dto.investigation import (
    InvestigationCreateDTO,
    InvestigationUpdateDTO,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    RiskClassification,
)
from veritrace.domain.exceptions.base import (
    EntityNotFoundError,
    InvalidStateTransitionError,
    ValidationError,
)
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import (
    OrganizationModel,
)
from veritrace.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing isolated SQLite database path."""
    return tmp_path / "test_inv_service.sqlite"


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    """Fixture providing Alembic Config pointing to temp DB."""
    cfg = Config("alembic.ini")
    url = f"sqlite:///{db_path.as_posix()}"
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_create_investigation_success_and_audit(db_path: Path, alembic_config: Config) -> None:
    """Verify creating an investigation persists record and records CASE_CREATED audit event."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            session.add(
                OrganizationModel(
                    id=org_id,
                    name="Global Steel Works",
                    industry_sector="MANUFACTURING",
                    created_at=datetime.now(UTC),
                )
            )

        service = InvestigationService(lambda: SqlAlchemyUnitOfWork(session_factory))
        dto = InvestigationCreateDTO(
            title="Procurement Manipulation Audit",
            reference_code="INV-2026-001",
            organization_id=org_id,
        )

        res = service.create_investigation(dto, actor_id="analyst_vikram")

        assert res.id.startswith("inv_")
        assert res.title == "Procurement Manipulation Audit"
        assert res.reference_code == "INV-2026-001"
        assert res.organization_id == org_id
        assert res.status == InvestigationStatus.DRAFT

        # Verify audit event was recorded
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            events = uow.audit_events.list_by_investigation(res.id, org_id)
            assert len(events) == 1
            assert events[0].event_type == AuditEventType.CASE_CREATED
            assert events[0].actor_id == "analyst_vikram"
    finally:
        engine.dispose()


def test_create_investigation_invalid_input_raises(db_path: Path, alembic_config: Config) -> None:
    """Verify empty title or reference code is rejected by Pydantic / Domain."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")

    try:
        with pytest.raises((PydanticValidationError, ValidationError)):
            InvestigationCreateDTO(
                title="",
                reference_code="INV-001",
                organization_id="org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001",
            )
    finally:
        engine.dispose()


def test_get_investigation_scoped_to_organization(db_path: Path, alembic_config: Config) -> None:
    """Verify retrieving investigation is strictly scoped to organization."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    org_1 = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    org_2 = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0002"

    try:
        now = datetime.now(UTC)
        with session_scope(session_factory) as session:
            session.add(
                OrganizationModel(id=org_1, name="Org One", industry_sector="BFSI", created_at=now)
            )
            session.add(
                OrganizationModel(id=org_2, name="Org Two", industry_sector="BFSI", created_at=now)
            )

        service = InvestigationService(lambda: SqlAlchemyUnitOfWork(session_factory))
        created = service.create_investigation(
            InvestigationCreateDTO(title="Case 1", reference_code="INV-01", organization_id=org_1)
        )

        # Successfully retrieved by owning org
        retrieved = service.get_investigation(created.id, org_1)
        assert retrieved is not None
        assert retrieved.id == created.id

        # Returns None when queried by non-owning org
        cross_retrieved = service.get_investigation(created.id, org_2)
        assert cross_retrieved is None
    finally:
        engine.dispose()


def test_list_investigations_and_update_metadata(db_path: Path, alembic_config: Config) -> None:
    """Verify listing and updating investigation permitted fields."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"

    try:
        with session_scope(session_factory) as session:
            session.add(
                OrganizationModel(
                    id=org_id,
                    name="Global Steel",
                    industry_sector="MANUFACTURING",
                    created_at=datetime.now(UTC),
                )
            )

        service = InvestigationService(lambda: SqlAlchemyUnitOfWork(session_factory))
        inv1 = service.create_investigation(
            InvestigationCreateDTO(
                title="First Case", reference_code="INV-001", organization_id=org_id
            )
        )
        inv2 = service.create_investigation(
            InvestigationCreateDTO(
                title="Second Case", reference_code="INV-002", organization_id=org_id
            )
        )

        assert inv2.id != inv1.id
        all_invs = service.list_investigations(org_id)
        assert len(all_invs) == 2

        # Update metadata
        updated = service.update_investigation(
            inv1.id,
            org_id,
            InvestigationUpdateDTO(
                title="Updated Case Title",
                risk_score=0.85,
                risk_classification=RiskClassification.SUSPECTED_MANIPULATION,
            ),
        )
        assert updated.title == "Updated Case Title"
        assert updated.risk_score == 0.85
        assert updated.risk_classification == RiskClassification.SUSPECTED_MANIPULATION

        # Transition status
        transitioned = service.transition_status(inv1.id, org_id, InvestigationStatus.PROCESSING)
        assert transitioned.status == InvestigationStatus.PROCESSING

        # Invalid transition raises error
        with pytest.raises(InvalidStateTransitionError):
            service.transition_status(inv1.id, org_id, InvestigationStatus.DRAFT)
    finally:
        engine.dispose()


def test_update_nonexistent_investigation_raises(db_path: Path, alembic_config: Config) -> None:
    """Verify updating nonexistent investigation raises EntityNotFoundError."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)

    try:
        service = InvestigationService(lambda: SqlAlchemyUnitOfWork(session_factory))
        with pytest.raises(EntityNotFoundError):
            service.update_investigation(
                "inv_00000000000000000000000000000000",
                "org_00000000000000000000000000000000",
                InvestigationUpdateDTO(title="New"),
            )
    finally:
        engine.dispose()
