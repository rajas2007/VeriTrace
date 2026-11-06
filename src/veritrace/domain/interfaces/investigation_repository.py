"""Protocol for Investigation repository operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.value_objects.identifiers import InvestigationId, OrganizationId


@runtime_checkable
class InvestigationRepository(Protocol):
    """Repository interface for managing Investigation aggregate roots."""

    def add(self, investigation: Investigation) -> None:
        """Persist a new Investigation entity within its assigned organization."""
        ...

    def get_by_id(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> Investigation | None:
        """Retrieve an investigation by ID scoped strictly to the specified organization."""
        ...

    def get_by_reference_code(
        self,
        reference_code: str,
        organization_id: OrganizationId,
    ) -> Investigation | None:
        """Retrieve an investigation by reference code scoped to the specified organization."""
        ...

    def list_by_organization(
        self,
        organization_id: OrganizationId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Investigation]:
        """List investigations belonging to an organization, ordered by created_at descending."""
        ...

    def update(
        self,
        investigation: Investigation,
        organization_id: OrganizationId,
    ) -> None:
        """Update an existing investigation, enforcing tenant ownership."""
        ...

    def count_by_organization(
        self,
        organization_id: OrganizationId,
    ) -> int:
        """Count total investigations belonging to an organization."""
        ...

    def delete(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> None:
        """Delete an investigation, enforcing tenant ownership."""
        ...
