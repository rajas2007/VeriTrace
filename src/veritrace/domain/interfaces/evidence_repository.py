"""Protocol for Evidence repository operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.value_objects.identifiers import (
    DocumentPageId,
    EvidenceId,
    InvestigationId,
    OrganizationId,
)


@runtime_checkable
class EvidenceRepository(Protocol):
    """Repository interface for managing visual Evidence crop anchors."""

    def add(self, evidence: Evidence, organization_id: OrganizationId) -> None:
        """Persist a visual evidence crop anchor, verifying parent page tenant ownership."""
        ...

    def get_by_id(
        self,
        evidence_id: EvidenceId,
        organization_id: OrganizationId,
    ) -> Evidence | None:
        """Retrieve an evidence anchor by ID scoped strictly to the authorized organization."""
        ...

    def list_by_page(
        self,
        page_id: DocumentPageId,
        organization_id: OrganizationId,
    ) -> list[Evidence]:
        """List visual evidence items anchored on a specific page, verifying tenant ownership."""
        ...

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Evidence]:
        """List all visual evidence items in an investigation, verifying tenant ownership."""
        ...
