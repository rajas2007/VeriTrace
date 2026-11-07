"""Crop-level forensic quality assessment for signature candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from veritrace.domain.exceptions.base import ValidationError


@dataclass(slots=True)
class SignatureCropQualityResult:
    """Quantitative assessment of signature crop quality and forensic adequacy.

    INVARIANT: Automated machine comparisons must be aborted when visual resolution,
    contrast, or blur prevents reliable optical stroke measurement. Inadequate crops
    must produce an explicit INSUFFICIENT_EVIDENCE finding preserved for human adjudication.
    """

    is_adequate: bool
    reasons: list[str] = field(default_factory=list)
    width_px: int = 0
    height_px: int = 0
    effective_dpi: int | None = None
    blur_score: float = 0.0  # Laplacian variance (higher = sharper)
    contrast_score: float = 0.0  # Intensity standard deviation
    stroke_coverage_pct: float = 0.0
    boundary_discontinuity: float = 0.0
    notes: str = ""


class SignatureCropQualityAssessor:
    """Evaluates multi-factor image quality metrics on cropped signature candidates.

    NOTE: Crop dimensions, Laplacian variance, contrast, stroke coverage, and
    boundary discontinuity thresholds are VeriTrace application-defined optical
    heuristics. They are not certified forensic standards and do not establish
    signature authenticity or authorship. Human examination remains necessary.
    """

    MIN_WIDTH_PX = 60
    MIN_HEIGHT_PX = 25
    MIN_DPI = 100
    BLUR_THRESHOLD = 35.0  # Laplacian variance threshold
    MIN_CONTRAST_STD = 15.0  # Intensity std dev threshold
    MIN_STROKE_COVERAGE_PCT = 0.20  # At least 0.20% ink pixels

    def evaluate(
        self,
        crop_image_or_path: np.ndarray | Path | str | bytes,
        effective_dpi: int | None = None,
    ) -> SignatureCropQualityResult:
        """Evaluate crop resolution, sharpness, contrast, and stroke density."""
        img = self._load_image(crop_image_or_path)
        h, w = img.shape[:2]

        reasons: list[str] = []

        # 1. Pixel Dimensions
        if w < self.MIN_WIDTH_PX or h < self.MIN_HEIGHT_PX:
            reasons.append(
                f"Insufficient crop dimensions ({w}x{h}px below minimum "
                f"{self.MIN_WIDTH_PX}x{self.MIN_HEIGHT_PX}px)"
            )

        # 2. Effective DPI
        if effective_dpi is not None and effective_dpi < self.MIN_DPI:
            reasons.append(
                f"Sub-standard resolution ({effective_dpi} DPI below {self.MIN_DPI} DPI threshold)"
            )

        # 3. Grayscale conversion
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 4. Blur / Sharpness (Laplacian variance)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap_var < self.BLUR_THRESHOLD:
            reasons.append(
                f"Severe optical blur detected "
                f"(Laplacian sharpness {lap_var:.1f} < {self.BLUR_THRESHOLD})"
            )

        # 5. Contrast (Intensity standard deviation)
        contrast = float(gray.std())
        if contrast < self.MIN_CONTRAST_STD:
            reasons.append(
                f"Low dynamic contrast ({contrast:.1f} < {self.MIN_CONTRAST_STD}); "
                "stroke and background separation is unreliable"
            )

        # 6. Stroke visibility / density
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        total_pixels = max(1, h * w)
        ink_pixels = int(np.count_nonzero(binary))
        coverage_pct = float((ink_pixels / total_pixels) * 100.0)

        if coverage_pct < self.MIN_STROKE_COVERAGE_PCT:
            reasons.append(
                f"Insufficient stroke density or resolution in cropped signature candidate "
                f"({coverage_pct:.2f}% < {self.MIN_STROKE_COVERAGE_PCT}%)"
            )

        # 7. Boundary clipping measurement (recorded for metric reporting, not as blur/res failure)
        top_edge = np.count_nonzero(binary[0, :])
        bottom_edge = np.count_nonzero(binary[-1, :])
        left_edge = np.count_nonzero(binary[:, 0])
        right_edge = np.count_nonzero(binary[:, -1])
        perimeter_ink = top_edge + bottom_edge + left_edge + right_edge
        perimeter_len = 2 * (h + w)
        boundary_disc = float(perimeter_ink / max(1, perimeter_len))

        is_adequate = len(reasons) == 0
        notes = (
            "Crop exhibits adequate optical resolution, contrast, and stroke definition "
            "for comparative analysis."
            if is_adequate
            else f"Forensic quality limitation: {'; '.join(reasons)}. Human review required."
        )

        return SignatureCropQualityResult(
            is_adequate=is_adequate,
            reasons=reasons,
            width_px=w,
            height_px=h,
            effective_dpi=effective_dpi,
            blur_score=lap_var,
            contrast_score=contrast,
            stroke_coverage_pct=coverage_pct,
            boundary_discontinuity=boundary_disc,
            notes=notes,
        )

    def _load_image(self, image_or_path: np.ndarray | Path | str | bytes) -> np.ndarray:
        if isinstance(image_or_path, np.ndarray):
            return image_or_path
        if isinstance(image_or_path, (str, Path)):
            p = Path(image_or_path)
            if not p.is_file():
                raise ValidationError(f"Signature crop image not found: {p}")
            img = cv2.imread(str(p))
            if img is None:
                raise ValidationError(f"Failed to decode image from path: {p}")
            return img
        if isinstance(image_or_path, bytes):
            nparr = np.frombuffer(image_or_path, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValidationError("Failed to decode image from bytes")
            return img
        raise TypeError(f"Unsupported image type: {type(image_or_path)}")
