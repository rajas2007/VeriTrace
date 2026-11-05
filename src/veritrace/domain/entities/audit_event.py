"""AuditEvent domain entity representing an immutable audit ledger entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.identifiers import (
    AUD_PREFIX,
    INV_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable append-only audit trail event for forensic chain-of-custody compliance."""

    id: str
    investigation_id: str
    event_type: AuditEventType
    actor_type: ActorType
    actor_id: str
    timestamp: datetime
    event_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", validate_id(self.id, AUD_PREFIX, "AuditEvent.id"))
        object.__setattr__(
            self,
            "investigation_id",
            validate_id(self.investigation_id, INV_PREFIX, "AuditEvent.investigation_id"),
        )
        if not self.actor_id or not self.actor_id.strip():
            raise ValidationError("AuditEvent.actor_id must not be empty")

        object.__setattr__(
            self,
            "timestamp",
            ensure_utc(self.timestamp, "AuditEvent.timestamp"),
        )

    @classmethod
    def create(
        cls,
        investigation_id: str,
        event_type: AuditEventType,
        actor_type: ActorType,
        actor_id: str,
        event_payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        """Factory method creating an immutable AuditEvent entity."""
        aid = event_id or generate_id(AUD_PREFIX)
        ts = timestamp or utc_now()
        payload = dict(event_payload) if event_payload else {}
        return cls(
            id=aid,
            investigation_id=investigation_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id.strip(),
            timestamp=ts,
            event_payload=payload,
        )
