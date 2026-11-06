"""Visual forensics analyzer coordinating ELA, font baseline, and evidence crop generation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from veritrace.capabilities.forensics.baseline import FontBaselineAnalyzer
from veritrace.capabilities.forensics.cropper import EvidenceCropper
from veritrace.capabilities.forensics.ela import ErrorLevelAnalyzer
from veritrace.capabilities.forensics.models import (
    BaselineAnomaly,
    ELAResult,
    ForensicProposal,
)
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory, FindingSeverity
from veritrace.domain.value_objects.identifiers import PAGE_PREFIX, generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken


@runtime_checkable
class VisualForensicsProtocol(Protocol):
    """Protocol for visual forensic analysis engines."""

    def compute_ela(self, image_path: Path, output_heatmap_path: Path | None = None) -> ELAResult:
        """Execute Error Level Analysis."""
        ...

    def detect_baseline_misalignments(
        self,
        tokens: list[ExtractedToken],
        page_width_px: int = 2550,
        page_height_px: int = 3300,
    ) -> list[BaselineAnomaly]:
        """Detect baseline misalignment anomalies in extracted tokens."""
        ...


class VisualForensicsAnalyzer:
    """Public orchestration facade for computer vision forensics and evidence generation."""

    def __init__(
        self,
        ela_analyzer: ErrorLevelAnalyzer | None = None,
        baseline_analyzer: FontBaselineAnalyzer | None = None,
        cropper: EvidenceCropper | None = None,
    ) -> None:
        self._ela_analyzer = ela_analyzer or ErrorLevelAnalyzer()
        self._baseline_analyzer = baseline_analyzer or FontBaselineAnalyzer()
        self._cropper = cropper or EvidenceCropper()

    def compute_ela(self, image_path: Path, output_heatmap_path: Path | None = None) -> ELAResult:
        """Delegate to ErrorLevelAnalyzer."""
        return self._ela_analyzer.compute_ela(image_path, output_heatmap_path)

    def detect_baseline_misalignments(
        self,
        tokens: list[ExtractedToken],
        page_width_px: int = 2550,
        page_height_px: int = 3300,
    ) -> list[BaselineAnomaly]:
        """Delegate to FontBaselineAnalyzer."""
        return self._baseline_analyzer.detect_baseline_misalignments(
            tokens, page_width_px=page_width_px, page_height_px=page_height_px
        )

    def analyze_page(
        self,
        image_or_path: np.ndarray | Path | bytes,
        tokens: list[ExtractedToken],
        output_dir: Path,
        page_number: int = 1,
        page_id: str | None = None,
    ) -> tuple[list[ForensicProposal], list[Evidence]]:
        """Run complete visual forensic pipeline on a single document page.

        Extracts:
        1. ELA compression variance anomalies and heatmap.
        2. Font baseline regression misalignments.
        3. Pixel-anchored high-resolution evidence crops with 20px padding.

        Returns:
            Tuple of (list of ForensicProposals, list of created Evidence entities).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        effective_page_id = page_id or generate_id(PAGE_PREFIX)
        img_canvas = self._cropper._load_image(image_or_path)
        img_h, img_w = img_canvas.shape[:2]

        proposals: list[ForensicProposal] = []
        evidence_entities: list[Evidence] = []

        # 1. Error Level Analysis (ELA)
        heatmap_path = output_dir / f"page_{page_number:04d}_ela_heatmap.png"
        ela_res = self._ela_analyzer.compute_ela(
            image_or_path=image_or_path, output_heatmap_path=heatmap_path
        )

        if ela_res.anomaly_detected:
            for idx, region in enumerate(ela_res.anomalous_regions):
                crop_path = output_dir / f"page_{page_number:04d}_ela_crop_{idx + 1:02d}.png"
                try:
                    ev = self._cropper.create_evidence_entity(
                        page_id=effective_page_id,
                        image_or_path=image_or_path,
                        bbox=region,
                        output_crop_path=crop_path,
                        heatmap_image_path=str(heatmap_path) if heatmap_path.exists() else None,
                        grounding_explanation=(
                            f"Localized compression differential detected via Error Level Analysis "
                            f"(score: {ela_res.anomaly_score:.2f})."
                        ),
                    )
                    evidence_entities.append(ev)
                except Exception:
                    continue

                severity = (
                    FindingSeverity.HIGH if ela_res.anomaly_score > 0.6 else FindingSeverity.MEDIUM
                )
                prop = ForensicProposal(
                    category=FindingCategory.ELA_COMPRESSION_VARIANCE,
                    epistemic_tier=EpistemicTier.SUSPECTED_MANIPULATION,
                    severity=severity,
                    title="Localized Compression Level Discontinuity (ELA)",
                    narrative_explanation=(
                        f"Error Level Analysis identified a localized compression differential "
                        f"on page {page_number} (anomaly score: {ela_res.anomaly_score:.2f}). "
                        f"Surrounding pixels exhibit different re-compression degradation "
                        f"characteristics, consistent with a spliced or digitally modified patch."
                    ),
                    confidence=min(1.0, 0.70 + (ela_res.anomaly_score * 0.25)),
                    normalized_bbox=region,
                    evidence_crop_path=crop_path,
                    evidence_heatmap_path=heatmap_path,
                    measurements={
                        "global_mean_error": ela_res.global_mean_error,
                        "global_std_error": ela_res.global_std_error,
                        "max_local_error": ela_res.max_local_error,
                        "anomaly_score": ela_res.anomaly_score,
                    },
                )
                proposals.append(prop)

        # 2. Font Baseline Misalignment Analysis
        if tokens:
            baseline_anomalies = self._baseline_analyzer.detect_baseline_misalignments(
                tokens, page_width_px=img_w, page_height_px=img_h
            )

            for b_idx, anom in enumerate(baseline_anomalies):
                crop_path = output_dir / f"page_{page_number:04d}_baseline_crop_{b_idx + 1:02d}.png"
                try:
                    ev = self._cropper.create_evidence_entity(
                        page_id=effective_page_id,
                        image_or_path=image_or_path,
                        bbox=anom.normalized_bbox,
                        output_crop_path=crop_path,
                        grounding_explanation=(
                            f"Token '{anom.token_text}' deviates "
                            f"{anom.baseline_residual_sigma:.1f}σ "
                            f"({anom.baseline_residual_px:.1f}px) from line baseline."
                        ),
                    )
                    evidence_entities.append(ev)
                except Exception:
                    continue

                # Higher severity if token looks like numeric amount or contains digits
                is_numeric = any(char.isdigit() for char in anom.token_text)
                severity = FindingSeverity.HIGH if is_numeric else FindingSeverity.MEDIUM

                prop = ForensicProposal(
                    category=FindingCategory.FONT_BASELINE_MISALIGNMENT,
                    epistemic_tier=EpistemicTier.SUSPECTED_MANIPULATION,
                    severity=severity,
                    title=f"Font Baseline Misalignment on '{anom.token_text}'",
                    narrative_explanation=(
                        f"Extracted token '{anom.token_text}' on page {page_number} deviates "
                        f"{anom.baseline_residual_px:.1f}px ({anom.baseline_residual_sigma:.1f}σ) "
                        f"from the fitted baseline of line {anom.line_index + 1}. "
                        f"Isolated vertical displacement indicates potential numeral splicing."
                    ),
                    confidence=min(1.0, 0.65 + min(0.30, anom.baseline_residual_sigma * 0.05)),
                    normalized_bbox=anom.normalized_bbox,
                    evidence_crop_path=crop_path,
                    measurements={
                        "residual_px": anom.baseline_residual_px,
                        "residual_sigma": anom.baseline_residual_sigma,
                        "line_index": anom.line_index,
                        "line_slope": anom.line_slope,
                    },
                )
                proposals.append(prop)

        return proposals, evidence_entities
