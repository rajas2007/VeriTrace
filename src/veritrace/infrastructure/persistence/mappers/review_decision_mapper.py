"""Bidirectional mapper between ReviewDecision domain entity and ReviewDecisionModel."""

from __future__ import annotations

from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.enums.forensic import ReviewDecisionType
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.review_decision import (
    ReviewDecisionModel,
)


class ReviewDecisionMapper:
    """Maps between ReviewDecision domain entity and SQLAlchemy ReviewDecisionModel."""

    @staticmethod
    def to_model(entity: ReviewDecision) -> ReviewDecisionModel:
        """Convert ReviewDecision domain entity to SQLAlchemy model."""
        return ReviewDecisionModel(
            id=entity.id,
            finding_id=entity.finding_id,
            reviewer_id=entity.reviewer_id,
            decision=entity.decision.value,
            rationale=entity.rationale,
            timestamp=to_utc(entity.timestamp),
        )

    @staticmethod
    def to_entity(model: ReviewDecisionModel) -> ReviewDecision:
        """Convert SQLAlchemy ReviewDecisionModel to ReviewDecision domain entity."""
        timestamp = to_utc(model.timestamp)
        assert timestamp is not None
        return ReviewDecision(
            id=model.id,
            finding_id=model.finding_id,
            reviewer_id=model.reviewer_id,
            decision=ReviewDecisionType(model.decision),
            rationale=model.rationale,
            timestamp=timestamp,
        )
