"""Unit tests verifying Finding invariants: epistemic scale, AI exclusion, and review."""

import pytest

from veritrace.domain.entities.finding import Finding
from veritrace.domain.enums.audit import ActorType
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    ReviewStatus,
)
from veritrace.domain.exceptions import (
    AiModificationForbiddenError,
    ConfidenceRangeError,
    InvalidIdentifierError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    EVD_PREFIX,
    INV_PREFIX,
    generate_id,
)


def _make_finding(
    severity: FindingSeverity = FindingSeverity.MEDIUM,
    epistemic_tier: EpistemicTier = EpistemicTier.DETECTED_INCONSISTENCY,
    confidence: float = 0.85,
) -> Finding:
    return Finding.create(
        investigation_id=generate_id(INV_PREFIX),
        category=FindingCategory.TEMPORAL_CONTRADICTION,
        epistemic_tier=epistemic_tier,
        severity=severity,
        title="Delivery date precedes PO issue date",
        narrative_explanation=(
            "Challan shows delivery on 2026-01-05 but PO was issued on 2026-01-12."
        ),
        confidence=confidence,
    )


def test_severity_confidence_epistemic_tier_independence() -> None:
    """Verify that severity, confidence, and epistemic tier vary independently."""
    # Low severity, confirmed observation, high confidence
    f1 = _make_finding(
        severity=FindingSeverity.LOW,
        epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
        confidence=0.99,
    )
    assert f1.severity == FindingSeverity.LOW
    assert f1.epistemic_tier == EpistemicTier.CONFIRMED_OBSERVATION
    assert f1.confidence == 0.99

    # Critical severity, detected inconsistency, moderate confidence
    f2 = _make_finding(
        severity=FindingSeverity.CRITICAL,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        confidence=0.65,
    )
    assert f2.severity == FindingSeverity.CRITICAL
    assert f2.epistemic_tier == EpistemicTier.DETECTED_INCONSISTENCY
    assert f2.confidence == 0.65

    # High severity, suspected manipulation, low-medium confidence
    f3 = _make_finding(
        severity=FindingSeverity.HIGH,
        epistemic_tier=EpistemicTier.SUSPECTED_MANIPULATION,
        confidence=0.45,
    )
    assert f3.severity == FindingSeverity.HIGH
    assert f3.epistemic_tier == EpistemicTier.SUSPECTED_MANIPULATION
    assert f3.confidence == 0.45


def test_finding_confidence_range_validation() -> None:
    """Verify confidence must be strictly within [0.0, 1.0]."""
    inv_id = generate_id(INV_PREFIX)
    with pytest.raises(ConfidenceRangeError):
        Finding.create(
            investigation_id=inv_id,
            category=FindingCategory.ARITHMETIC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.HIGH,
            title="Tax sum mismatch",
            narrative_explanation="Calculated tax differs from invoice total",
            confidence=1.05,
        )


def test_ai_creation_forbidden() -> None:
    """Verify AI synthesizer is strictly prohibited from creating domain findings."""
    inv_id = generate_id(INV_PREFIX)
    with pytest.raises(AiModificationForbiddenError) as exc_info:
        Finding.create(
            investigation_id=inv_id,
            category=FindingCategory.COPY_MOVE_CLONE,
            epistemic_tier=EpistemicTier.SUSPECTED_MANIPULATION,
            severity=FindingSeverity.CRITICAL,
            title="Cloned seal region",
            narrative_explanation="Duplicate seal detected across documents",
            actor_type=ActorType.AI_SYNTHESIZER,
        )
    assert "AI_SYNTHESIZER is strictly prohibited" in str(exc_info.value)


def test_ai_adjudication_forbidden() -> None:
    """Verify AI cannot confirm, dismiss, annotate, or modify severity/tier of findings."""
    finding = _make_finding()

    # AI confirm forbidden
    with pytest.raises(AiModificationForbiddenError):
        finding.confirm(
            reviewer_id="subj_ai",
            rationale="AI validated this finding",
            actor_type=ActorType.AI_SYNTHESIZER,
        )

    # AI dismiss forbidden
    with pytest.raises(AiModificationForbiddenError):
        finding.dismiss(
            reviewer_id="subj_ai",
            rationale="AI dismissed this finding",
            actor_type=ActorType.AI_SYNTHESIZER,
        )

    # AI annotate forbidden
    with pytest.raises(AiModificationForbiddenError):
        finding.annotate(
            reviewer_id="subj_ai",
            notes="AI added note",
            actor_type=ActorType.AI_SYNTHESIZER,
        )

    # AI update_severity forbidden
    with pytest.raises(AiModificationForbiddenError):
        finding.update_severity(
            new_severity=FindingSeverity.CRITICAL,
            actor_type=ActorType.AI_SYNTHESIZER,
        )

    # AI update_epistemic_tier forbidden
    with pytest.raises(AiModificationForbiddenError):
        finding.update_epistemic_tier(
            new_tier=EpistemicTier.CONFIRMED_OBSERVATION,
            actor_type=ActorType.AI_SYNTHESIZER,
        )

    # AI update_narrative forbidden
    with pytest.raises(AiModificationForbiddenError):
        finding.update_narrative(
            narrative="AI rewritten narrative",
            actor_type=ActorType.AI_SYNTHESIZER,
        )


def test_human_investigator_review_workflow() -> None:
    """Verify human reviewer confirmation, dismissal, annotation, and updates."""
    finding = _make_finding()
    assert finding.review_status == ReviewStatus.PENDING_REVIEW

    # Annotate
    finding.annotate(
        reviewer_id="subj_analyst1",
        notes="Checked bank statement, invoice amounts do not reconcile.",
        actor_type=ActorType.HUMAN_ANALYST,
    )
    assert finding.review_status == ReviewStatus.ANNOTATED
    assert "Checked bank statement" in (finding.investigator_guidance or "")

    # Update severity
    finding.update_severity(
        new_severity=FindingSeverity.CRITICAL,
        actor_type=ActorType.HUMAN_ANALYST,
    )
    assert finding.severity == FindingSeverity.CRITICAL

    # Update epistemic tier
    finding.update_epistemic_tier(
        new_tier=EpistemicTier.SUSPECTED_MANIPULATION,
        actor_type=ActorType.HUMAN_ANALYST,
    )
    assert finding.epistemic_tier == EpistemicTier.SUSPECTED_MANIPULATION

    # Update narrative
    finding.update_narrative(
        narrative="Updated reconciliation narrative after forensic bank ledger check.",
        actor_type=ActorType.HUMAN_ANALYST,
    )
    assert "reconciliation narrative" in finding.narrative_explanation

    # Confirm
    finding.confirm(
        reviewer_id="subj_analyst1",
        rationale="Vendor confirmed discrepancy in writing.",
        actor_type=ActorType.HUMAN_ANALYST,
    )
    assert finding.review_status == ReviewStatus.CONFIRMED

    # Dismiss requires rationale
    f2 = _make_finding()
    with pytest.raises(ValidationError):
        f2.dismiss("subj_analyst1", rationale="", actor_type=ActorType.HUMAN_ANALYST)

    f2.dismiss(
        "subj_analyst1",
        rationale="Resolved as rounding discrepancy < Rs 1",
        actor_type=ActorType.HUMAN_ANALYST,
    )
    assert f2.review_status == ReviewStatus.DISMISSED


def test_evidence_linking_and_unlinking() -> None:
    """Verify evidence crops can be linked and unlinked with strict evd_ prefix validation."""
    finding = _make_finding()
    ev1 = generate_id(EVD_PREFIX)
    ev2 = generate_id(EVD_PREFIX)

    assert ev1.startswith("evd_")
    assert ev2.startswith("evd_")

    finding.link_evidence(ev1)
    finding.link_evidence(ev2)
    assert len(finding.evidence_ids) == 2
    assert ev1 in finding.evidence_ids
    assert ev2 in finding.evidence_ids

    # Duplicate linking is a no-op
    finding.link_evidence(ev1)
    assert len(finding.evidence_ids) == 2

    # Linking non-evidence ID raises
    inv_id = generate_id(INV_PREFIX)
    with pytest.raises(InvalidIdentifierError):
        finding.link_evidence(inv_id)

    # Unlink
    finding.unlink_evidence(ev1)
    assert len(finding.evidence_ids) == 1
    assert ev1 not in finding.evidence_ids


def test_evidence_ids_immutable_frozenset() -> None:
    """Verify evidence_ids property returns frozenset preventing direct mutation bypass."""
    finding = _make_finding()
    ev_id = generate_id(EVD_PREFIX)
    finding.link_evidence(ev_id)

    ev_view = finding.evidence_ids
    assert isinstance(ev_view, frozenset)
    with pytest.raises(AttributeError):
        ev_view.add("evd_fake123456789012345678901234")  # type: ignore[attr-defined]


def test_legacy_evidence_prefix_rejected_by_finding() -> None:
    """Verify legacy ev_ prefix is rejected when linking to a Finding."""
    finding = _make_finding()
    legacy_ev = "ev_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"

    with pytest.raises(InvalidIdentifierError):
        finding.link_evidence(legacy_ev)

    inv_id = generate_id(INV_PREFIX)
    with pytest.raises(InvalidIdentifierError):
        Finding.create(
            investigation_id=inv_id,
            category=FindingCategory.TEMPORAL_CONTRADICTION,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.LOW,
            title="Title",
            narrative_explanation="Narrative",
            evidence_ids={legacy_ev},
        )
