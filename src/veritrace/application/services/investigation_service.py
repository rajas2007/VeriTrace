"""Application service for Investigation case management."""

from __future__ import annotations

from collections.abc import Callable

from veritrace.application.dto.investigation import (
    InvestigationCreateDTO,
    InvestigationResponseDTO,
    InvestigationUpdateDTO,
)
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.investigation import InvestigationStatus
from veritrace.domain.exceptions.base import EntityNotFoundError
from veritrace.domain.interfaces.unit_of_work import UnitOfWork


class InvestigationService:
    """Coordinates lifecycle, retrieval, and updates for Investigation cases."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork] | UnitOfWork) -> None:
        if callable(uow_factory):
            self._uow_factory = uow_factory
        else:
            self._uow_factory = lambda: uow_factory

    def _get_uow(self) -> UnitOfWork:
        return self._uow_factory()

    def create_investigation(
        self,
        dto: InvestigationCreateDTO,
        actor_id: str = "analyst_01",
    ) -> InvestigationResponseDTO:
        """Create a new investigation aggregate within an organization and record audit trail."""
        inv = Investigation.create(
            title=dto.title,
            reference_code=dto.reference_code,
            organization_id=dto.organization_id,
        )

        with self._get_uow() as uow:
            uow.investigations.add(inv)

            actor_type = (
                ActorType.HUMAN_ANALYST
                if "analyst" in actor_id.lower()
                else ActorType.SYSTEM_PIPELINE
            )
            audit_event = AuditEvent.create(
                investigation_id=inv.id,
                event_type=AuditEventType.CASE_CREATED,
                actor_type=actor_type,
                actor_id=actor_id,
                event_payload={
                    "title": inv.title,
                    "reference_code": inv.reference_code,
                    "organization_id": dto.organization_id,
                },
            )
            uow.audit_events.add(audit_event, dto.organization_id)

        assert inv.organization_id is not None
        return InvestigationResponseDTO(
            id=inv.id,
            organization_id=inv.organization_id,
            title=inv.title,
            reference_code=inv.reference_code,
            status=inv.status,
            risk_score=inv.risk_score,
            risk_classification=inv.risk_classification,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    def get_investigation(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> InvestigationResponseDTO | None:
        """Retrieve an investigation by ID, strictly enforcing organization ownership."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                return None
            assert inv.organization_id is not None
            return InvestigationResponseDTO(
                id=inv.id,
                organization_id=inv.organization_id,
                title=inv.title,
                reference_code=inv.reference_code,
                status=inv.status,
                risk_score=inv.risk_score,
                risk_classification=inv.risk_classification,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )

    def list_investigations(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[InvestigationResponseDTO]:
        """List investigations belonging to an organization in descending order of creation."""
        with self._get_uow() as uow:
            items = uow.investigations.list_by_organization(organization_id, skip=skip, limit=limit)
            results: list[InvestigationResponseDTO] = []
            for inv in items:
                assert inv.organization_id is not None
                results.append(
                    InvestigationResponseDTO(
                        id=inv.id,
                        organization_id=inv.organization_id,
                        title=inv.title,
                        reference_code=inv.reference_code,
                        status=inv.status,
                        risk_score=inv.risk_score,
                        risk_classification=inv.risk_classification,
                        created_at=inv.created_at,
                        updated_at=inv.updated_at,
                    )
                )
            return results

    def update_investigation(
        self,
        investigation_id: str,
        organization_id: str,
        dto: InvestigationUpdateDTO,
        actor_id: str = "analyst_01",
    ) -> InvestigationResponseDTO:
        """Update permitted investigation metadata enforcing tenant ownership."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"Investigation '{investigation_id}' not found in '{organization_id}'"
                )

            if dto.title is not None:
                inv.title = dto.title
            if dto.reference_code is not None:
                inv.reference_code = dto.reference_code
            if dto.risk_score is not None:
                inv.update_risk_score(dto.risk_score, dto.risk_classification)

            uow.investigations.update(inv, organization_id)

            assert inv.organization_id is not None
            return InvestigationResponseDTO(
                id=inv.id,
                organization_id=inv.organization_id,
                title=inv.title,
                reference_code=inv.reference_code,
                status=inv.status,
                risk_score=inv.risk_score,
                risk_classification=inv.risk_classification,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )

    def transition_status(
        self,
        investigation_id: str,
        organization_id: str,
        new_status: InvestigationStatus,
        actor_id: str = "analyst_01",
    ) -> InvestigationResponseDTO:
        """Transition an investigation according to lifecycle rules."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"Investigation '{investigation_id}' not found in '{organization_id}'"
                )

            inv.transition_to(new_status)
            uow.investigations.update(inv, organization_id)

            assert inv.organization_id is not None
            return InvestigationResponseDTO(
                id=inv.id,
                organization_id=inv.organization_id,
                title=inv.title,
                reference_code=inv.reference_code,
                status=inv.status,
                risk_score=inv.risk_score,
                risk_classification=inv.risk_classification,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )
