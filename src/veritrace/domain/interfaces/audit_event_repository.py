"""Protocol for AuditEvent repository operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.value_objects.identifiers import (
    AuditEventId,
    InvestigationId,
    OrganizationId,
)


@runtime_checkable
class AuditEventRepository(Protocol):
    """Repository interface for appending and querying immutable AuditEvent records.

    INVARIANT: Append-only ledger. Update and delete operations are strictly prohibited.
    """

    def add(self, event: AuditEvent, organization_id: OrganizationId) -> None:
        """Append a new audit event, verifying investigation tenant ownership."""
        ...

    def get_by_id(
        self,
        event_id: AuditEventId,
        organization_id: OrganizationId,
    ) -> AuditEvent | None:
        """Retrieve an audit event by ID scoped strictly to the authorized organization."""
        ...

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[AuditEvent]:
        """Retrieve audit events for an investigation in deterministic chronological order."""
        ...
