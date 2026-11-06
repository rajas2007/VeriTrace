"""SQLite implementation of EvidenceRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.exceptions.base import EntityNotFoundError, TenantIsolationError
from veritrace.domain.value_objects.identifiers import (
    DocumentPageId,
    EvidenceId,
    InvestigationId,
    OrganizationId,
)
from veritrace.infrastructure.persistence.mappers.evidence_mapper import EvidenceMapper
from veritrace.infrastructure.persistence.models.document import DocumentModel
from veritrace.infrastructure.persistence.models.document_page import DocumentPageModel
from veritrace.infrastructure.persistence.models.evidence import EvidenceModel
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel


class SqliteEvidenceRepository:
    """SQLite-backed repository for visual Evidence crop anchors."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, evidence: Evidence, organization_id: OrganizationId) -> None:
        """Persist visual evidence crop anchor, verifying parent page tenant ownership."""
        page = self._session.execute(
            select(DocumentPageModel)
            .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentPageModel.id == str(evidence.page_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if page is None:
            any_page = self._session.get(DocumentPageModel, str(evidence.page_id))
            if any_page is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: DocumentPage '{evidence.page_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"DocumentPage '{evidence.page_id}' not found in organization '{organization_id}'"
            )

        model = EvidenceMapper.to_model(evidence)
        self._session.add(model)
        self._session.flush()

    def get_by_id(
        self,
        evidence_id: EvidenceId,
        organization_id: OrganizationId,
    ) -> Evidence | None:
        """Retrieve an evidence anchor by ID scoped strictly to the authorized organization."""
        stmt = (
            select(EvidenceModel)
            .join(DocumentPageModel, EvidenceModel.page_id == DocumentPageModel.id)
            .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                EvidenceModel.id == str(evidence_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return EvidenceMapper.to_entity(row)

    def list_by_page(
        self,
        page_id: DocumentPageId,
        organization_id: OrganizationId,
    ) -> list[Evidence]:
        """List visual evidence items anchored on a specific page, verifying tenant ownership."""
        page = self._session.execute(
            select(DocumentPageModel)
            .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentPageModel.id == str(page_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if page is None:
            any_page = self._session.get(DocumentPageModel, str(page_id))
            if any_page is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: DocumentPage '{page_id}' does not belong "
                    f"to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"DocumentPage '{page_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(EvidenceModel)
            .where(EvidenceModel.page_id == str(page_id))
            .order_by(EvidenceModel.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [EvidenceMapper.to_entity(r) for r in rows]

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Evidence]:
        """List visual evidence items across all pages, verifying tenant ownership."""
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
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{investigation_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(EvidenceModel)
            .join(DocumentPageModel, EvidenceModel.page_id == DocumentPageModel.id)
            .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
            .where(DocumentModel.investigation_id == str(investigation_id))
            .order_by(EvidenceModel.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [EvidenceMapper.to_entity(r) for r in rows]
