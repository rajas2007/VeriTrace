"""Bidirectional mapper between Finding domain entity and FindingModel."""

from __future__ import annotations

from collections.abc import Iterable

from veritrace.domain.entities.finding import Finding
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    ReviewStatus,
)
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.finding import FindingModel


class FindingMapper:
    """Maps between Finding domain entity and SQLAlchemy FindingModel."""

    @staticmethod
    def to_model(entity: Finding) -> FindingModel:
        """Convert Finding domain entity to SQLAlchemy model.

        Note: Associations in finding_evidence_map are managed via relationship or session.
        """
        return FindingModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            category=entity.category.value,
            epistemic_tier=entity.epistemic_tier.value,
            severity=entity.severity.value,
            title=entity.title,
            narrative_explanation=entity.narrative_explanation,
            confidence=entity.confidence,
            investigator_guidance=entity.investigator_guidance,
            review_status=entity.review_status.value,
            signature_reference_id=entity.signature_reference_id,
            created_at=to_utc(entity.created_at),
        )

    @staticmethod
    def to_entity(
        model: FindingModel,
        evidence_ids: Iterable[str] | None = None,
    ) -> Finding:
        """Convert SQLAlchemy FindingModel to Finding domain entity."""
        created_at = to_utc(model.created_at)
        assert created_at is not None

        ev_set: set[str] = set()
        if evidence_ids is not None:
            ev_set = set(evidence_ids)
        elif hasattr(model, "evidence") and model.evidence is not None:
            ev_set = {e.id for e in model.evidence}

        return Finding(
            id=model.id,
            investigation_id=model.investigation_id,
            category=FindingCategory(model.category),
            epistemic_tier=EpistemicTier(model.epistemic_tier),
            severity=FindingSeverity(model.severity),
            title=model.title,
            narrative_explanation=model.narrative_explanation,
            created_at=created_at,
            confidence=model.confidence,
            investigator_guidance=model.investigator_guidance,
            review_status=ReviewStatus(model.review_status),
            signature_reference_id=model.signature_reference_id,
            _evidence_ids=ev_set,
        )

    to_domain = to_entity
