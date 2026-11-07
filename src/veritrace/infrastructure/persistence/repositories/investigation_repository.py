"""SQLite implementation of InvestigationRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.cross_document_relation import CrossDocumentRelation
from veritrace.domain.entities.dossier import Dossier
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.exceptions.base import EntityNotFoundError, TenantIsolationError
from veritrace.domain.value_objects.identifiers import InvestigationId, OrganizationId
from veritrace.infrastructure.persistence.mappers.cross_document_relation_mapper import (
    CrossDocumentRelationMapper,
)
from veritrace.infrastructure.persistence.mappers.dossier_mapper import DossierMapper
from veritrace.infrastructure.persistence.mappers.investigation_mapper import (
    InvestigationMapper,
)
from veritrace.infrastructure.persistence.models.cross_document_relation import (
    CrossDocumentRelationModel,
)
from veritrace.infrastructure.persistence.models.document import DocumentModel
from veritrace.infrastructure.persistence.models.dossier import DossierModel
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel


class SqliteInvestigationRepository:
    """SQLite-backed repository for Investigation aggregate roots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, investigation: Investigation) -> None:
        """Persist a new Investigation entity within its assigned organization."""
        model = InvestigationMapper.to_model(investigation)
        self._session.add(model)
        self._session.flush()

    def get_by_id(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> Investigation | None:
        """Retrieve an investigation by ID scoped strictly to the specified organization."""
        stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(investigation_id),
            InvestigationModel.organization_id == str(organization_id),
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return InvestigationMapper.to_entity(row)

    def get_by_reference_code(
        self,
        reference_code: str,
        organization_id: OrganizationId,
    ) -> Investigation | None:
        """Retrieve an investigation by reference code scoped to the specified organization."""
        stmt = select(InvestigationModel).where(
            InvestigationModel.reference_code == reference_code,
            InvestigationModel.organization_id == str(organization_id),
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return InvestigationMapper.to_entity(row)

    def list_by_organization(
        self,
        organization_id: OrganizationId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Investigation]:
        """List investigations belonging to an organization, ordered by created_at descending."""
        stmt = (
            select(InvestigationModel)
            .where(InvestigationModel.organization_id == str(organization_id))
            .order_by(InvestigationModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [InvestigationMapper.to_entity(r) for r in rows]

    def update(
        self,
        investigation: Investigation,
        organization_id: OrganizationId,
    ) -> None:
        """Update an existing investigation, enforcing tenant ownership."""
        stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(investigation.id),
            InvestigationModel.organization_id == str(organization_id),
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            any_model = self._session.get(InvestigationModel, str(investigation.id))
            if any_model is not None:
                raise TenantIsolationError(
                    f"Cross-organization access violation: Investigation '{investigation.id}' "
                    f"belongs to '{any_model.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{investigation.id}' not found in organization '{organization_id}'"
            )

        model.title = investigation.title
        model.reference_code = investigation.reference_code
        model.status = investigation.status.value
        model.risk_score = investigation.risk_score
        model.risk_classification = investigation.risk_classification.value
        model.updated_at = investigation.updated_at
        self._session.flush()

    def count_by_organization(self, organization_id: OrganizationId) -> int:
        """Count total investigations belonging to an organization."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(InvestigationModel)
            .where(InvestigationModel.organization_id == str(organization_id))
        )
        return int(self._session.execute(stmt).scalar() or 0)

    def delete(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> None:
        """Delete an investigation, enforcing tenant ownership."""
        stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(investigation_id),
            InvestigationModel.organization_id == str(organization_id),
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            any_model = self._session.get(InvestigationModel, str(investigation_id))
            if any_model is not None:
                raise TenantIsolationError(
                    f"Cross-organization access violation: Investigation '{investigation_id}' "
                    f"belongs to '{any_model.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{investigation_id}' not found in organization '{organization_id}'"
            )
        self._session.delete(model)
        self._session.flush()

    def add_relation(
        self,
        relation: CrossDocumentRelation,
        organization_id: OrganizationId,
    ) -> None:
        """Persist a CrossDocumentRelation, verifying tenant ownership."""
        inv_stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(relation.investigation_id),
            InvestigationModel.organization_id == str(organization_id),
        )
        inv = self._session.execute(inv_stmt).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(relation.investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{relation.investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{relation.investigation_id}' not found "
                f"in organization '{organization_id}'"
            )

        for doc_id, label in [
            (relation.source_document_id, "Source document"),
            (relation.target_document_id, "Target document"),
        ]:
            doc_stmt = (
                select(DocumentModel)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentModel.id == str(doc_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            doc_model = self._session.execute(doc_stmt).scalar_one_or_none()
            if doc_model is None:
                any_doc = self._session.get(DocumentModel, str(doc_id))
                if any_doc is not None:
                    doc_inv = self._session.get(InvestigationModel, any_doc.investigation_id)
                    if doc_inv is not None and doc_inv.organization_id != str(organization_id):
                        raise TenantIsolationError(
                            f"Cross-organization violation: {label} '{doc_id}' belongs to "
                            f"organization '{doc_inv.organization_id}', not '{organization_id}'"
                        )
                raise EntityNotFoundError(
                    f"{label} '{doc_id}' not found in organization '{organization_id}'"
                )

        model = CrossDocumentRelationMapper.to_model(relation)
        self._session.add(model)
        self._session.flush()

    def list_relations(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[CrossDocumentRelation]:
        """List all CrossDocumentRelation entities belonging to an investigation."""
        inv_stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(investigation_id),
            InvestigationModel.organization_id == str(organization_id),
        )
        inv = self._session.execute(inv_stmt).scalar_one_or_none()
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

        stmt = select(CrossDocumentRelationModel).where(
            CrossDocumentRelationModel.investigation_id == str(investigation_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [CrossDocumentRelationMapper.to_entity(r) for r in rows]

    def add_dossier(
        self,
        dossier: Dossier,
        organization_id: OrganizationId,
    ) -> None:
        """Persist a compiled Dossier entity, verifying tenant ownership."""
        inv_stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(dossier.investigation_id),
            InvestigationModel.organization_id == str(organization_id),
        )
        inv = self._session.execute(inv_stmt).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(dossier.investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{dossier.investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{dossier.investigation_id}' "
                f"not found in organization '{organization_id}'"
            )

        model = DossierMapper.to_model(dossier)
        self._session.add(model)
        self._session.flush()

    def list_dossiers(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Dossier]:
        """List all compiled Dossier entities for an investigation."""
        inv_stmt = select(InvestigationModel).where(
            InvestigationModel.id == str(investigation_id),
            InvestigationModel.organization_id == str(organization_id),
        )
        inv = self._session.execute(inv_stmt).scalar_one_or_none()
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
            select(DossierModel)
            .where(DossierModel.investigation_id == str(investigation_id))
            .order_by(DossierModel.generated_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [DossierMapper.to_entity(r) for r in rows]
