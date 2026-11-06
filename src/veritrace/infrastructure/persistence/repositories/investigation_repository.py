"""SQLite implementation of InvestigationRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.exceptions.base import EntityNotFoundError, TenantIsolationError
from veritrace.domain.value_objects.identifiers import InvestigationId, OrganizationId
from veritrace.infrastructure.persistence.mappers.investigation_mapper import (
    InvestigationMapper,
)
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
