"""Entity domain model representing a reconciled canonical identity or fact."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.enums.audit import EntityType
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.identifiers import (
    ENT_PREFIX,
    INV_PREFIX,
    generate_id,
    validate_id,
)


@dataclass(slots=True)
class Entity:
    """Canonical real-world identity or factual claim reconciled across multiple documents."""

    id: str
    investigation_id: str
    entity_type: EntityType
    canonical_value: str

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, ENT_PREFIX, "Entity.id")
        self.investigation_id = validate_id(
            self.investigation_id, INV_PREFIX, "Entity.investigation_id"
        )
        if not self.canonical_value or not self.canonical_value.strip():
            raise ValidationError("Entity.canonical_value must not be empty")

    @classmethod
    def create(
        cls,
        investigation_id: str,
        entity_type: EntityType,
        canonical_value: str,
        entity_id: str | None = None,
    ) -> Entity:
        """Factory method creating a canonical Entity."""
        eid = entity_id or generate_id(ENT_PREFIX)
        return cls(
            id=eid,
            investigation_id=investigation_id,
            entity_type=entity_type,
            canonical_value=canonical_value.strip(),
        )
