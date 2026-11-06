"""Page Quality Assessment Coordinator.

Aggregates image measurements, PDF structural metrics, and text quality
for an individual document page into a unified PageQualityResult.
"""

from pathlib import Path

import numpy as np
from PIL import Image

from veritrace.capabilities.quality.image_quality import ImageQualityAnalyzer
from veritrace.capabilities.quality.models import (
    PageQualityResult,
    PdfStructuralMetrics,
    QualityIssue,
)
from veritrace.capabilities.quality.rules import DEFAULT_THRESHOLDS, QualityThresholds
from veritrace.capabilities.quality.scoring import QualityScorer
from veritrace.capabilities.quality.text_quality import TextQualityAnalyzer


class PageQualityAnalyzer:
    """Evaluates an individual page across all relevant quality dimensions."""

    def __init__(
        self,
        thresholds: QualityThresholds | None = None,
        scorer: QualityScorer | None = None,
    ) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.scorer = scorer or QualityScorer()
        self.image_analyzer = ImageQualityAnalyzer(self.thresholds)
        self.text_analyzer = TextQualityAnalyzer(self.thresholds)

    def analyze_page(
        self,
        image_input: str | Path | Image.Image | np.ndarray | None = None,
        text_input: str | None = None,
        pdf_metrics: PdfStructuralMetrics | None = None,
        page_number: int = 1,
    ) -> PageQualityResult:
        """Run multi-dimensional quality assessment on a single page.

        Args:
            image_input: Rendered or scanned image for this page (optional if image not available).
            text_input: Extracted text for this page (optional).
            pdf_metrics: Pre-computed PDF structural metrics (optional).
            page_number: 1-based page sequence number.

        Returns:
            PageQualityResult containing all metrics, detected issues, and deterministic score.
        """
        all_issues: list[QualityIssue] = []

        # 1. Image Quality Dimension
        img_metrics = None
        if image_input is not None:
            img_metrics, img_issues = self.image_analyzer.analyze(
                image_input, page_number=page_number
            )
            all_issues.extend(img_issues)

        # 2. PDF Structural Dimension
        if pdf_metrics is not None:
            # Propagate page number if needed
            pass

        # 3. Text Quality Dimension
        txt_metrics = None
        if text_input is not None:
            width_pt = pdf_metrics.width_points if pdf_metrics else None
            height_pt = pdf_metrics.height_points if pdf_metrics else None
            txt_metrics, txt_issues = self.text_analyzer.analyze_page_text(
                text=text_input,
                page_number=page_number,
                page_width_points=width_pt,
                page_height_points=height_pt,
            )
            all_issues.extend(txt_issues)

        # 4. Deterministic scoring
        score, category, recommendation, penalties = self.scorer.compute_page_score(all_issues)

        return PageQualityResult(
            page_number=page_number,
            score=score,
            category=category,
            recommendation=recommendation,
            issues=all_issues,
            image_metrics=img_metrics,
            pdf_metrics=pdf_metrics,
            text_metrics=txt_metrics,
            penalties=penalties,
        )
