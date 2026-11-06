"""Bidirectional mapper between AuditEvent domain entity and AuditEventModel."""

from __future__ import annotations

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.audit_event import AuditEventModel


class AuditEventMapper:
    """Maps between AuditEvent domain entity and SQLAlchemy AuditEventModel."""

    @staticmethod
    def to_model(entity: AuditEvent) -> AuditEventModel:
        """Convert AuditEvent domain entity to SQLAlchemy model."""
        return AuditEventModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            event_type=entity.event_type.value,
            actor_type=entity.actor_type.value,
            actor_id=entity.actor_id,
            timestamp=to_utc(entity.timestamp),
            event_payload=entity.event_payload,
        )

    @staticmethod
    def to_entity(model: AuditEventModel) -> AuditEvent:
        """Convert SQLAlchemy AuditEventModel to AuditEvent domain entity."""
        timestamp = to_utc(model.timestamp)
        assert timestamp is not None
        return AuditEvent(
            id=model.id,
            investigation_id=model.investigation_id,
            event_type=AuditEventType(model.event_type),
            actor_type=ActorType(model.actor_type),
            actor_id=model.actor_id,
            timestamp=timestamp,
            event_payload=model.event_payload,
        )

    to_domain = to_entity
