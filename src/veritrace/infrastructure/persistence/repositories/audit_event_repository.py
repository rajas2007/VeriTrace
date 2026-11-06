"""SQLite implementation of AuditEventRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.exceptions.base import EntityNotFoundError, TenantIsolationError
from veritrace.domain.value_objects.identifiers import (
    AuditEventId,
    InvestigationId,
    OrganizationId,
)
from veritrace.infrastructure.persistence.mappers.audit_event_mapper import (
    AuditEventMapper,
)
from veritrace.infrastructure.persistence.models.audit_event import AuditEventModel
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel


class SqliteAuditEventRepository:
    """SQLite-backed repository for immutable AuditEvent records.

    INVARIANT: Append-only ledger. Update and delete methods are strictly omitted.
    Protected at database engine level by SQLite BEFORE UPDATE and BEFORE DELETE triggers.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: AuditEvent, organization_id: OrganizationId) -> None:
        """Append a new audit event, verifying investigation tenant ownership."""
        inv = self._session.execute(
            select(InvestigationModel).where(
                InvestigationModel.id == str(event.investigation_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(event.investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{event.investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{event.investigation_id}' not found "
                f"in organization '{organization_id}'"
            )

        model = AuditEventMapper.to_model(event)
        self._session.add(model)
        self._session.flush()

    def get_by_id(
        self,
        event_id: AuditEventId,
        organization_id: OrganizationId,
    ) -> AuditEvent | None:
        """Retrieve an audit event by ID scoped strictly to the authorized organization."""
        stmt = (
            select(AuditEventModel)
            .join(InvestigationModel, AuditEventModel.investigation_id == InvestigationModel.id)
            .where(
                AuditEventModel.id == str(event_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return AuditEventMapper.to_entity(row)

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[AuditEvent]:
        """Retrieve audit events for an investigation in deterministic chronological order."""
        inv = self._session.execute(
            select(InvestigationModel).where(
                InvestigationModel.id == str(investigation_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{investigation_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.investigation_id == str(investigation_id))
            .order_by(AuditEventModel.timestamp.asc(), AuditEventModel.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [AuditEventMapper.to_entity(r) for r in rows]
