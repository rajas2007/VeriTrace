"""Signature stroke characteristic and boundary artifact analyzer."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.forensic import SignatureEstimate, SignatureMeasurement
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


class SignatureStrokeAnalyzer:
    """Measures 2D optical stroke geometry and boundary clipping discontinuities

    from a localized signature image patch.
    """

    def analyze_crop(
        self,
        crop_image_or_path: np.ndarray | Path | bytes,
        normalized_bbox: NormalizedBoundingBox,
    ) -> tuple[SignatureMeasurement, SignatureEstimate]:
        """Compute physical stroke measurements and optical smoothness estimates.

        Args:
            crop_image_or_path: Cropped signature patch.
            normalized_bbox: Original bounding box of the crop on the document page.

        Returns:
            Tuple of (SignatureMeasurement, SignatureEstimate).
        """
        img = self._load_image(crop_image_or_path)
        h, w = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 1. Binarize stroke ink vs paper background
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        total_pixels = h * w
        dark_pixels = int(np.count_nonzero(binary))
        coverage_pct = float((dark_pixels / max(1, total_pixels)) * 100.0)

        # 2. Measure apparent stroke width via Euclidean Distance Transform
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        # Stroke widths correspond to local maxima in distance transform (radius * 2)
        # Sample positive distances representing ink strokes
        stroke_radii = dist_transform[binary > 0]
        if len(stroke_radii) > 0:
            stroke_widths = stroke_radii * 2.0
            stroke_mean = float(np.mean(stroke_widths))
            stroke_var = float(np.var(stroke_widths))
        else:
            stroke_mean = 0.0
            stroke_var = 0.0

        # 3. Detect boundary clipping mask discontinuities
        # If a signature was cut and pasted digitally, the outer perimeter pixels
        # often show a rectangular mask edge with sudden ink termination.
        boundary_mask_score = self._measure_boundary_discontinuity(binary)

        # 4. Optical stroke curvature / smoothness heuristic
        smoothness = self._measure_stroke_smoothness(binary)

        measurement = SignatureMeasurement(
            normalized_bbox=normalized_bbox,
            apparent_stroke_width_mean_px=max(0.0, stroke_mean),
            apparent_stroke_width_variance_px=max(0.0, stroke_var),
            stroke_pixel_coverage_pct=min(100.0, max(0.0, coverage_pct)),
            boundary_mask_discontinuity=min(1.0, max(0.0, boundary_mask_score)),
        )

        estimate = SignatureEstimate(
            apparent_stroke_smoothness=min(1.0, max(0.0, smoothness)),
        )

        return measurement, estimate

    def _measure_boundary_discontinuity(self, binary: np.ndarray) -> float:
        """Measure if strokes terminate abruptly along the rectangular outer perimeter."""
        h, w = binary.shape[:2]
        if h < 10 or w < 10:
            return 0.0

        # Sample border pixels (top, bottom, left, right edges)
        top_edge = binary[0, :]
        bottom_edge = binary[h - 1, :]
        left_edge = binary[:, 0]
        right_edge = binary[:, w - 1]

        border_ink_pixels = (
            np.count_nonzero(top_edge)
            + np.count_nonzero(bottom_edge)
            + np.count_nonzero(left_edge)
            + np.count_nonzero(right_edge)
        )
        total_border_pixels = 2 * (h + w)

        border_ratio = border_ink_pixels / max(1, total_border_pixels)
        # Natural signatures terminate inside box; abrupt rectangular cuts have high border ratio
        discontinuity_score = min(1.0, border_ratio * 4.0)
        return float(discontinuity_score)

    def _measure_stroke_smoothness(self, binary: np.ndarray) -> float:
        """Estimate stroke curvature smoothness based on contour arc length and hull convexity."""
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.0

        solidity_scores: list[float] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 30:
                continue
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity_scores.append(area / hull_area)

        if solidity_scores:
            # High fluid curvature produces moderate, steady solidity
            return float(np.mean(solidity_scores))
        return 0.5

    def _load_image(self, image_or_path: np.ndarray | Path | bytes) -> np.ndarray:
        """Decode input into OpenCV BGR ndarray."""
        if isinstance(image_or_path, np.ndarray):
            return image_or_path

        if isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise ValidationError(f"Image not found: {image_or_path}")
            img = cv2.imread(str(image_or_path))
            if img is None:
                raise ValidationError(f"Failed to decode image from path: {image_or_path}")
            return img

        if isinstance(image_or_path, bytes):
            nparr = np.frombuffer(image_or_path, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValidationError("Failed to decode image from bytes")
            return img

        raise TypeError(f"Unsupported image type: {type(image_or_path)}")
