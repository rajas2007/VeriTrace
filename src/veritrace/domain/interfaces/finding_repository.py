"""Protocol for Finding repository operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.entities.finding import Finding
from veritrace.domain.value_objects.identifiers import (
    FindingId,
    InvestigationId,
    OrganizationId,
)


@runtime_checkable
class FindingRepository(Protocol):
    """Repository interface for managing standardized forensic Finding entities."""

    def add(self, finding: Finding, organization_id: OrganizationId) -> None:
        """Persist a new Finding with evidence links, verifying tenant ownership."""
        ...

    def get_by_id(
        self,
        finding_id: FindingId,
        organization_id: OrganizationId,
    ) -> Finding | None:
        """Retrieve a finding with linked evidence IDs, scoped strictly to the organization."""
        ...

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Finding]:
        """List all findings for an investigation, enforcing tenant ownership."""
        ...

    def update(
        self,
        finding: Finding,
        organization_id: OrganizationId,
    ) -> None:
        """Update an existing finding and its evidence associations, enforcing tenant ownership."""
        ...

    def delete(
        self,
        finding_id: FindingId,
        organization_id: OrganizationId,
    ) -> None:
        """Delete an unadjudicated finding, enforcing tenant ownership."""
        ...
