"""ReviewDecision domain entity capturing human examiner oversight."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from veritrace.domain.enums.forensic import ReviewDecisionType
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.identifiers import (
    FND_PREFIX,
    REV_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)


@dataclass(slots=True)
class ReviewDecision:
    """Authoritative sign-off, dismissal, or annotation decision made by an investigator."""

    id: str
    finding_id: str
    reviewer_id: str
    decision: ReviewDecisionType
    rationale: str
    timestamp: datetime

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, REV_PREFIX, "ReviewDecision.id")
        self.finding_id = validate_id(self.finding_id, FND_PREFIX, "ReviewDecision.finding_id")
        if not self.reviewer_id or not self.reviewer_id.strip():
            raise ValidationError("ReviewDecision.reviewer_id must not be empty")
        if not self.rationale or not self.rationale.strip():
            raise ValidationError("ReviewDecision.rationale must not be empty")
        self.timestamp = ensure_utc(self.timestamp, "ReviewDecision.timestamp")

    @classmethod
    def create(
        cls,
        finding_id: str,
        reviewer_id: str,
        decision: ReviewDecisionType,
        rationale: str,
        decision_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> ReviewDecision:
        """Factory method creating a ReviewDecision entity."""
        rid = decision_id or generate_id(REV_PREFIX)
        ts = timestamp or utc_now()
        return cls(
            id=rid,
            finding_id=finding_id,
            reviewer_id=reviewer_id.strip(),
            decision=decision,
            rationale=rationale.strip(),
            timestamp=ts,
        )
