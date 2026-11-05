"""Bidirectional mapper between Investigation domain entity and InvestigationModel."""

from __future__ import annotations

from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    RiskClassification,
)
from veritrace.domain.exceptions.base import ValidationError
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel


class InvestigationMapper:
    """Maps between Investigation domain entity and SQLAlchemy InvestigationModel."""

    @staticmethod
    def to_model(entity: Investigation) -> InvestigationModel:
        """Convert Investigation domain entity to SQLAlchemy model.

        Enforces mandatory organization ownership: an investigation cannot be persisted
        without being bound to an organization workspace.
        """
        if not entity.organization_id or not entity.organization_id.strip():
            raise ValidationError(
                "Investigation.organization_id must not be empty; every investigation "
                "must belong to an organization"
            )

        return InvestigationModel(
            id=entity.id,
            title=entity.title,
            reference_code=entity.reference_code,
            status=entity.status.value,
            risk_score=entity.risk_score,
            risk_classification=entity.risk_classification.value,
            organization_id=entity.organization_id,
            created_at=to_utc(entity.created_at),
            updated_at=to_utc(entity.updated_at),
        )

    @staticmethod
    def to_entity(model: InvestigationModel) -> Investigation:
        """Convert SQLAlchemy InvestigationModel to Investigation domain entity."""
        created_at = to_utc(model.created_at)
        updated_at = to_utc(model.updated_at)
        assert created_at is not None
        assert updated_at is not None
        return Investigation(
            id=model.id,
            title=model.title,
            reference_code=model.reference_code,
            status=InvestigationStatus(model.status),
            created_at=created_at,
            updated_at=updated_at,
            risk_score=model.risk_score,
            risk_classification=RiskClassification(model.risk_classification),
            organization_id=model.organization_id,
        )
