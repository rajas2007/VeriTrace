"""Forensics, findings, and evidence domain enums."""

from enum import StrEnum


class FindingCategory(StrEnum):
    """Categorization of forensic anomalies and analytical results."""

    ELA_COMPRESSION_VARIANCE = "ELA_COMPRESSION_VARIANCE"
    FONT_BASELINE_MISALIGNMENT = "FONT_BASELINE_MISALIGNMENT"
    COPY_MOVE_CLONE = "COPY_MOVE_CLONE"
    ARITHMETIC_MISMATCH = "ARITHMETIC_MISMATCH"
    TEMPORAL_CONTRADICTION = "TEMPORAL_CONTRADICTION"
    CROSS_DOC_MISMATCH = "CROSS_DOC_MISMATCH"
    SIGNATURE_VERIFICATION = "SIGNATURE_VERIFICATION"
    METADATA_DISCREPANCY = "METADATA_DISCREPANCY"


class EpistemicTier(StrEnum):
    """Three-Tier Epistemic Scale separating factual claims from hypotheses.

    INVARIANT: A finding's epistemic tier represents its ontological certainty,
    which is strictly distinct from both its severity (impact) and confidence (probability).
    """

    CONFIRMED_OBSERVATION = "CONFIRMED_OBSERVATION"
    DETECTED_INCONSISTENCY = "DETECTED_INCONSISTENCY"
    SUSPECTED_MANIPULATION = "SUSPECTED_MANIPULATION"


class FindingSeverity(StrEnum):
    """Four-level impact severity scale for investigation findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReviewStatus(StrEnum):
    """Human investigator review lifecycle state on a finding."""

    PENDING_REVIEW = "PENDING_REVIEW"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    ANNOTATED = "ANNOTATED"


class ReviewDecisionType(StrEnum):
    """Authoritative adjudication decision rendered by a human examiner."""

    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    ANNOTATED = "ANNOTATED"


class RelationType(StrEnum):
    """Semantic cross-document relational link type."""

    CONFLICTS_WITH = "CONFLICTS_WITH"
    CORROBORATES = "CORROBORATES"
    SUPPLEMENTS = "SUPPLEMENTS"


class SignatureAssessmentLevel(StrEnum):
    """Standardized Six-Level Epistemic Assessment Scale for Signature Forensics."""

    SIGNATURE_DETECTED = "SIGNATURE_DETECTED"
    VISUAL_ANOMALY_OBSERVED = "VISUAL_ANOMALY_OBSERVED"
    SIMILARITY_WITH_REFERENCE = "SIMILARITY_WITH_REFERENCE"
    POSSIBLE_MANIPULATION_INDICATOR = "POSSIBLE_MANIPULATION_INDICATOR"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HUMAN_EXAMINER_DECISION = "HUMAN_EXAMINER_DECISION"
