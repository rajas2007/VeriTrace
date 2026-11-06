"""Font baseline linear regression engine detecting numeral and text splice anomalies."""

from __future__ import annotations

import numpy as np

from veritrace.capabilities.forensics.models import BaselineAnomaly
from veritrace.domain.value_objects.provenance import ExtractedToken


class FontBaselineAnalyzer:
    """Analyzes text line baselines using linear regression to detect spliced characters."""

    def __init__(
        self,
        sigma_threshold: float = 2.5,
        min_residual_px: float = 3.0,
        min_tokens_per_line: int = 3,
        line_vertical_tolerance_ratio: float = 0.5,
    ) -> None:
        self._sigma_threshold = sigma_threshold
        self._min_residual_px = min_residual_px
        self._min_tokens_per_line = min_tokens_per_line
        self._line_vertical_tol = line_vertical_tolerance_ratio

    def group_tokens_into_lines(self, tokens: list[ExtractedToken]) -> list[list[ExtractedToken]]:
        """Group tokens into physical text lines based on spatial vertical alignment."""
        if not tokens:
            return []

        # Sort tokens primarily by vertical top (ymin), secondarily by left (xmin)
        sorted_tokens = sorted(
            tokens, key=lambda t: (t.normalized_bbox.ymin, t.normalized_bbox.xmin)
        )

        lines: list[list[ExtractedToken]] = []
        for tok in sorted_tokens:
            tok_mid_y = (tok.normalized_bbox.ymin + tok.normalized_bbox.ymax) / 2.0
            tok_h = tok.normalized_bbox.ymax - tok.normalized_bbox.ymin

            placed = False
            for line in lines:
                line_ymin = min(t.normalized_bbox.ymin for t in line)
                line_ymax = max(t.normalized_bbox.ymax for t in line)
                line_mid_y = (line_ymin + line_ymax) / 2.0
                line_avg_h = float(
                    np.mean([t.normalized_bbox.ymax - t.normalized_bbox.ymin for t in line])
                )
                overlap = min(tok.normalized_bbox.ymax, line_ymax) - max(
                    tok.normalized_bbox.ymin, line_ymin
                )
                max_h = max(tok_h, line_avg_h)
                tolerance = max_h * self._line_vertical_tol

                within_tol = abs(tok_mid_y - line_mid_y) <= tolerance
                min_h = min(tok_h, line_avg_h)
                if overlap > 0.15 * min_h or within_tol:
                    line.append(tok)
                    placed = True
                    break

            if not placed:
                lines.append([tok])

        # Sort tokens within each line from left to right (xmin)
        for line in lines:
            line.sort(key=lambda t: t.normalized_bbox.xmin)

        return lines

    def detect_baseline_misalignments(
        self,
        tokens: list[ExtractedToken],
        page_width_px: int = 2550,
        page_height_px: int = 3300,
    ) -> list[BaselineAnomaly]:
        """Detect tokens whose baseline deviates anomalously (> 2.5 sigma) from line regression.

        Args:
            tokens: List of ExtractedTokens with normalized bounding boxes.
            page_width_px: Page resolution width.
            page_height_px: Page resolution height.

        Returns:
            List of detected BaselineAnomaly instances.
        """
        lines = self.group_tokens_into_lines(tokens)
        anomalies: list[BaselineAnomaly] = []

        for line_idx, line in enumerate(lines):
            if len(line) < self._min_tokens_per_line:
                continue

            # Extract bottom coordinates (baseline in page pixels) and x-centers
            xs = np.array(
                [
                    ((t.normalized_bbox.xmin + t.normalized_bbox.xmax) / 2.0) * page_width_px
                    for t in line
                ],
                dtype=np.float64,
            )
            # Baseline is bottom edge (ymax in pixels)
            ys = np.array(
                [t.normalized_bbox.ymax * page_height_px for t in line],
                dtype=np.float64,
            )

            # Fit ordinary least squares linear regression y = m*x + c
            # Using robust fitting: if x values are nearly identical, skip
            if np.max(xs) - np.min(xs) < 10.0:
                continue

            try:
                poly = np.polyfit(xs, ys, deg=1)
                slope, intercept = float(poly[0]), float(poly[1])
            except Exception:
                continue

            # Predicted baseline coordinates
            predicted_ys = slope * xs + intercept
            residuals = ys - predicted_ys
            abs_residuals = np.abs(residuals)

            # Robust standard deviation via Median Absolute Deviation (MAD)
            # avoids outlier contamination when a single numeral is spliced
            med_res = float(np.median(residuals))
            mad = float(np.median(np.abs(residuals - med_res)))
            sigma = 1.4826 * mad if mad > 0.001 else float(np.std(residuals))

            if sigma <= 0.001:
                continue

            for tok_idx, tok in enumerate(line):
                res_px = float(abs_residuals[tok_idx])
                # Compute distance from median baseline trend in sigma
                res_sigma = float(abs(residuals[tok_idx] - med_res) / sigma)

                # Check if deviation exceeds both relative sigma and absolute pixel threshold
                if res_sigma >= self._sigma_threshold and res_px >= self._min_residual_px:
                    anomalies.append(
                        BaselineAnomaly(
                            line_index=line_idx,
                            token_text=tok.raw_text,
                            token_index_in_line=tok_idx,
                            baseline_residual_px=res_px,
                            baseline_residual_sigma=res_sigma,
                            normalized_bbox=tok.normalized_bbox,
                            line_slope=slope,
                            line_intercept=intercept,
                        )
                    )

        return anomalies
