"""Bidirectional mapper between Organization domain entity and OrganizationModel."""

from __future__ import annotations

from veritrace.domain.entities.organization import Organization
from veritrace.domain.enums.audit import IndustrySector
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.organization import OrganizationModel


class OrganizationMapper:
    """Maps between Organization domain entity and SQLAlchemy OrganizationModel."""

    @staticmethod
    def to_model(entity: Organization) -> OrganizationModel:
        """Convert Organization domain entity to SQLAlchemy model."""
        return OrganizationModel(
            id=entity.id,
            name=entity.name,
            industry_sector=entity.industry_sector.value,
            created_at=to_utc(entity.created_at),
        )

    @staticmethod
    def to_entity(model: OrganizationModel) -> Organization:
        """Convert SQLAlchemy OrganizationModel to Organization domain entity."""
        created_at = to_utc(model.created_at)
        assert created_at is not None
        return Organization(
            id=model.id,
            name=model.name,
            industry_sector=IndustrySector(model.industry_sector),
            created_at=created_at,
        )
