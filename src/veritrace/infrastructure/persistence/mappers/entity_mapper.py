"""Bidirectional mapper between Entity domain model and EntityModel."""

from __future__ import annotations

from veritrace.domain.entities.entity import Entity
from veritrace.domain.enums.audit import EntityType
from veritrace.infrastructure.persistence.models.entity import EntityModel


class EntityMapper:
    """Maps between Entity domain model and SQLAlchemy EntityModel."""

    @staticmethod
    def to_model(entity: Entity) -> EntityModel:
        """Convert Entity domain model to SQLAlchemy model."""
        return EntityModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            entity_type=entity.entity_type.value,
            canonical_value=entity.canonical_value,
        )

    @staticmethod
    def to_entity(model: EntityModel) -> Entity:
        """Convert SQLAlchemy EntityModel to Entity domain model."""
        return Entity(
            id=model.id,
            investigation_id=model.investigation_id,
            entity_type=EntityType(model.entity_type),
            canonical_value=model.canonical_value,
        )
