"""Finding domain entity representing an analytical conclusion or forensic observation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from veritrace.domain.enums.audit import ActorType
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    ReviewStatus,
)
from veritrace.domain.exceptions.base import (
    AiModificationForbiddenError,
    ConfidenceRangeError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    EVD_PREFIX,
    FND_PREFIX,
    INV_PREFIX,
    SIGREF_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)


@dataclass(slots=True)
class Finding:
    """Standardized forensic conclusion categorized under the Three-Tier Epistemic Ontology.

    CRITICAL INVARIANTS:
    1. Severity, Confidence, and Epistemic Tier are strictly independent concepts:
       - Severity: impact or importance of the finding (LOW, MEDIUM, HIGH, CRITICAL).
       - Confidence: reliability or detector probability of the measurement [0.0 - 1.0].
       - Epistemic Tier: ontological nature of claim (OBSERVATION, INCONSISTENCY, MANIPULATION).
    2. A visual anomaly or signature mismatch must NOT automatically be treated as confirmed fraud.
    3. AI (AI_SYNTHESIZER) is strictly prohibited from creating, modifying, confirming, dismissing,
       annotating, or altering the severity/tier of domain findings.
    4. Direct mutation of the evidence associations collection is protected by returning an
       immutable frozenset; associations must be made through link_evidence() / unlink_evidence().
    """

    id: str
    investigation_id: str
    category: FindingCategory
    epistemic_tier: EpistemicTier
    severity: FindingSeverity
    title: str
    narrative_explanation: str
    created_at: datetime
    confidence: float = 1.0
    investigator_guidance: str | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    signature_reference_id: str | None = None
    _evidence_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, FND_PREFIX, "Finding.id")
        self.investigation_id = validate_id(
            self.investigation_id, INV_PREFIX, "Finding.investigation_id"
        )
        if not self.title or not self.title.strip():
            raise ValidationError("Finding.title must not be empty")
        if not self.narrative_explanation or not self.narrative_explanation.strip():
            raise ValidationError("Finding.narrative_explanation must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ConfidenceRangeError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.signature_reference_id is not None:
            if self.signature_reference_id.startswith(SIGREF_PREFIX):
                self.signature_reference_id = validate_id(
                    self.signature_reference_id,
                    SIGREF_PREFIX,
                    "Finding.signature_reference_id",
                )
            elif self.signature_reference_id.startswith("sig_"):
                self.signature_reference_id = validate_id(
                    self.signature_reference_id,
                    "sig_",
                    "Finding.signature_reference_id",
                )

        self.created_at = ensure_utc(self.created_at, "Finding.created_at")

        # Validate pre-existing evidence IDs against canonical evd_ prefix
        validated_evs = set()
        for ev_id in self._evidence_ids:
            validated_evs.add(validate_id(ev_id, EVD_PREFIX, "evidence_id"))
        self._evidence_ids = validated_evs

    @property
    def evidence_ids(self) -> frozenset[str]:
        """Immutable view of visual evidence IDs (evd_<hex>) supporting this finding."""
        return frozenset(self._evidence_ids)

    def confirm(
        self,
        reviewer_id: str,
        rationale: str,
        actor_type: ActorType = ActorType.HUMAN_ANALYST,
    ) -> None:
        """Confirm the finding with mandatory human justification."""
        self._assert_human_actor(actor_type, "confirm finding")
        if not reviewer_id or not reviewer_id.strip():
            raise ValidationError("reviewer_id must not be empty")
        if not rationale or not rationale.strip():
            raise ValidationError("rationale must not be empty when confirming a finding")

        self.review_status = ReviewStatus.CONFIRMED

    def dismiss(
        self,
        reviewer_id: str,
        rationale: str,
        actor_type: ActorType = ActorType.HUMAN_ANALYST,
    ) -> None:
        """Dismiss the finding as benign artifact or false positive with human justification."""
        self._assert_human_actor(actor_type, "dismiss finding")
        if not reviewer_id or not reviewer_id.strip():
            raise ValidationError("reviewer_id must not be empty")
        if not rationale or not rationale.strip():
            raise ValidationError("rationale must not be empty when dismissing a finding")

        self.review_status = ReviewStatus.DISMISSED

    def annotate(
        self,
        reviewer_id: str,
        notes: str,
        actor_type: ActorType = ActorType.HUMAN_ANALYST,
    ) -> None:
        """Attach investigator commentary to the finding."""
        self._assert_human_actor(actor_type, "annotate finding")
        if not reviewer_id or not reviewer_id.strip():
            raise ValidationError("reviewer_id must not be empty")
        if not notes or not notes.strip():
            raise ValidationError("notes must not be empty")

        self.review_status = ReviewStatus.ANNOTATED
        if self.investigator_guidance:
            self.investigator_guidance += f"\n[Annotated by {reviewer_id}]: {notes.strip()}"
        else:
            self.investigator_guidance = f"[Annotated by {reviewer_id}]: {notes.strip()}"

    def update_severity(
        self,
        new_severity: FindingSeverity,
        actor_type: ActorType = ActorType.HUMAN_ANALYST,
    ) -> None:
        """Update finding severity level (restricted to human investigator oversight)."""
        self._assert_human_actor(actor_type, "update finding severity")
        self.severity = new_severity

    def update_epistemic_tier(
        self,
        new_tier: EpistemicTier,
        actor_type: ActorType = ActorType.HUMAN_ANALYST,
    ) -> None:
        """Update finding epistemic tier (restricted to human investigator oversight)."""
        self._assert_human_actor(actor_type, "update finding epistemic tier")
        self.epistemic_tier = new_tier

    def update_narrative(
        self,
        narrative: str,
        actor_type: ActorType = ActorType.HUMAN_ANALYST,
    ) -> None:
        """Update finding narrative explanation (restricted to human investigator oversight)."""
        self._assert_human_actor(actor_type, "update finding narrative")
        if not narrative or not narrative.strip():
            raise ValidationError("narrative must not be empty")
        self.narrative_explanation = narrative.strip()

    def link_evidence(self, evidence_id: str) -> None:
        """Associate a visual evidence crop with this finding enforcing evd_ prefix."""
        valid_id = validate_id(evidence_id, EVD_PREFIX, "evidence_id")
        self._evidence_ids.add(valid_id)

    def unlink_evidence(self, evidence_id: str) -> None:
        """Remove a visual evidence crop association."""
        self._evidence_ids.discard(evidence_id)

    def _assert_human_actor(self, actor_type: ActorType, action: str) -> None:
        if actor_type == ActorType.AI_SYNTHESIZER:
            raise AiModificationForbiddenError(
                f"AI cannot {action}. Findings can only be adjudicated by a human investigator."
            )

    @classmethod
    def create(
        cls,
        investigation_id: str,
        category: FindingCategory,
        epistemic_tier: EpistemicTier,
        severity: FindingSeverity,
        title: str,
        narrative_explanation: str,
        confidence: float = 1.0,
        finding_id: str | None = None,
        investigator_guidance: str | None = None,
        review_status: ReviewStatus = ReviewStatus.PENDING_REVIEW,
        signature_reference_id: str | None = None,
        evidence_ids: set[str] | frozenset[str] | list[str] | None = None,
        actor_type: ActorType = ActorType.SYSTEM_PIPELINE,
        created_at: datetime | None = None,
    ) -> Finding:
        """Factory method creating a Finding entity."""
        if actor_type == ActorType.AI_SYNTHESIZER:
            raise AiModificationForbiddenError(
                "AI_SYNTHESIZER is strictly prohibited from creating domain findings."
            )

        fid = finding_id or generate_id(FND_PREFIX)
        ts = created_at or utc_now()
        ev_set = set(evidence_ids) if evidence_ids else set()

        return cls(
            id=fid,
            investigation_id=investigation_id,
            category=category,
            epistemic_tier=epistemic_tier,
            severity=severity,
            title=title.strip(),
            narrative_explanation=narrative_explanation.strip(),
            confidence=confidence,
            investigator_guidance=investigator_guidance,
            review_status=review_status,
            signature_reference_id=signature_reference_id,
            _evidence_ids=ev_set,
            created_at=ts,
        )
