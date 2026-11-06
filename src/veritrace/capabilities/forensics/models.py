"""Data models for visual forensics, ELA, font baseline, and evidence extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory, FindingSeverity
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


@dataclass(slots=True)
class ELAResult:
    """Quantitative result of Error Level Analysis on a document canvas."""

    global_mean_error: float
    global_std_error: float
    max_local_error: float
    anomaly_detected: bool
    anomaly_score: float  # [0.0 - 1.0]
    heatmap_path: Path | None = None
    anomalous_regions: list[NormalizedBoundingBox] = field(default_factory=list)
    quality_tested: int = 95
    scale_factor: int = 15


@dataclass(slots=True)
class BaselineAnomaly:
    """Detected vertical baseline misalignment on an extracted word or token."""

    line_index: int
    token_text: str
    token_index_in_line: int
    baseline_residual_px: float  # Vertical distance in pixels from regression line
    baseline_residual_sigma: float  # Distance measured in standard deviations (e.g. > 2.5)
    normalized_bbox: NormalizedBoundingBox
    line_slope: float
    line_intercept: float


@dataclass(slots=True)
class CopyMoveMatch:
    """Detected duplicate image patch (cloned signature or stamp) across regions or pages."""

    source_page: int
    source_bbox: NormalizedBoundingBox
    target_page: int
    target_bbox: NormalizedBoundingBox
    inlier_match_count: int
    similarity_score: float  # [0.0 - 1.0]
    match_type: str  # "SIGNATURE", "STAMP", "GRAPHIC"


@dataclass(slots=True)
class ForensicProposal:
    """Deterministic candidate finding proposed by visual forensic algorithms.

    In accordance with VeriTrace principles:
    - Anomaly is NOT proof of fraud or forgery.
    - AI does not decide or create findings.
    - Findings are mathematically grounded in deterministic CV measurements.
    """

    category: FindingCategory
    epistemic_tier: EpistemicTier
    severity: FindingSeverity
    title: str
    narrative_explanation: str
    confidence: float  # Measurement confidence [0.0 - 1.0]
    normalized_bbox: NormalizedBoundingBox | None = None
    evidence_crop_path: Path | None = None
    evidence_heatmap_path: Path | None = None
    measurements: dict[str, float | str | int | bool] = field(default_factory=dict)
