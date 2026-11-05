"""Signature forensic measurement, estimation, and analytical value objects."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.enums.forensic import SignatureAssessmentLevel
from veritrace.domain.exceptions.base import ConfidenceRangeError, ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


@dataclass(frozen=True, slots=True)
class SignatureMeasurement:
    """Physical features directly measurable from a static 2D scanned image."""

    normalized_bbox: NormalizedBoundingBox
    apparent_stroke_width_mean_px: float
    apparent_stroke_width_variance_px: float
    stroke_pixel_coverage_pct: float
    boundary_mask_discontinuity: float  # [0.0 - 1.0]
    is_clone_suspect: bool = False
    clone_match_doc_id: str | None = None

    def __post_init__(self) -> None:
        if self.apparent_stroke_width_mean_px < 0.0:
            raise ValidationError(
                f"stroke_width_mean must be non-negative: {self.apparent_stroke_width_mean_px}"
            )
        if self.apparent_stroke_width_variance_px < 0.0:
            raise ValidationError(
                f"stroke_width_variance must be >= 0: {self.apparent_stroke_width_variance_px}"
            )
        if not (0.0 <= self.stroke_pixel_coverage_pct <= 100.0):
            raise ValidationError(
                f"stroke_pixel_coverage_pct in [0.0, 100.0]: {self.stroke_pixel_coverage_pct}"
            )
        if not (0.0 <= self.boundary_mask_discontinuity <= 1.0):
            raise ConfidenceRangeError(
                f"boundary_mask_discontinuity in [0.0, 1.0]: {self.boundary_mask_discontinuity}"
            )


@dataclass(frozen=True, slots=True)
class SignatureEstimate:
    """Algorithmic estimates derived from 2D optical models.

    SCIENTIFIC INVARIANT: Static 2D scans cannot measure true 3D pen pressure,
    dynamic writing velocity, or chronological pen-lift sequencing.
    These fields represent visual optical approximations only.
    """

    apparent_stroke_smoothness: float  # Heuristic smoothness [0.0 - 1.0]
    metric_embedding_distance: float | None = None  # Distance metric >= 0.0
    comparison_reference_id: str | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.apparent_stroke_smoothness <= 1.0):
            raise ConfidenceRangeError(
                f"apparent_stroke_smoothness in [0.0, 1.0]: {self.apparent_stroke_smoothness}"
            )
        if self.metric_embedding_distance is not None and self.metric_embedding_distance < 0.0:
            raise ValidationError(
                f"metric_embedding_distance must be non-negative: {self.metric_embedding_distance}"
            )


@dataclass(frozen=True, slots=True)
class SignatureAnalysisResult:
    """Complete forensic evaluation payload for a localized signature."""

    signature_id: str  # Format: "sig_<uuid4_hex>"
    document_id: str
    page_number: int
    measurement: SignatureMeasurement
    estimate: SignatureEstimate
    assessment: SignatureAssessmentLevel
    uncertainty_score: float  # Epistemic uncertainty [0.0 - 1.0]
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.signature_id:
            raise ValidationError("signature_id must not be empty")
        if not self.document_id:
            raise ValidationError("document_id must not be empty")
        if self.page_number < 1:
            raise ValidationError(f"page_number must be >= 1: {self.page_number}")
        if not (0.0 <= self.uncertainty_score <= 1.0):
            raise ConfidenceRangeError(
                f"uncertainty_score must be in [0.0, 1.0]: {self.uncertainty_score}"
            )
