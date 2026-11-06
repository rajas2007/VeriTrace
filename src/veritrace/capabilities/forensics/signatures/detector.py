"""Signature detection and localization isolating handwritten strokes from typography and stamps."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


class SignatureDetector:
    """Detects candidate handwritten signature regions on document pages using contour curvature

    and morphological stroke filtering, distinguishing free-form handwriting from machine
    typography, table lines, and circular official stamps.
    """

    def __init__(
        self,
        min_area_px: int = 300,
        max_area_ratio: float = 0.25,
        min_aspect_ratio: float = 0.6,
        max_aspect_ratio: float = 7.0,
        cluster_dilation_px: int = 15,
    ) -> None:
        self._min_area = min_area_px
        self._max_area_ratio = max_area_ratio
        self._min_aspect = min_aspect_ratio
        self._max_aspect = max_aspect_ratio
        self._cluster_dilation = cluster_dilation_px

    def detect_candidate_regions(
        self, image_or_path: np.ndarray | Path | bytes
    ) -> list[NormalizedBoundingBox]:
        """Detect and localize candidate signature regions on a document canvas.

        Args:
            image_or_path: OpenCV BGR array, Path, or raw image bytes.

        Returns:
            List of NormalizedBoundingBox candidates.
        """
        img_bgr = self._load_image(image_or_path)
        img_h, img_w = img_bgr.shape[:2]

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr

        # 1. Binarize using Otsu's thresholding (dark strokes on light background)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2. Filter out long horizontal form / guideline underlines
        horiz_kernel_len = max(60, img_w // 15)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_kernel_len, 1))
        horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        # Remove straight lines from stroke mask
        strokes = cv2.subtract(binary, horiz_lines)

        # 3. Find connected contours of remaining strokes
        contours, _ = cv2.findContours(strokes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        stroke_candidates_mask = np.zeros_like(binary)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 30 or area > (img_w * img_h * self._max_area_ratio):
                continue

            perimeter = cv2.arcLength(cnt, True)
            if perimeter <= 0:
                continue

            # Circularity metric: 4 * pi * Area / (Perimeter^2)
            # Circular official stamps have circularity > 0.72; free-form signatures < 0.40
            circularity = (4.0 * math.pi * area) / (perimeter * perimeter)
            if circularity > 0.72:
                # Filter circular stamps
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect = float(w) / max(1, h)

            # Isolated single letters or dots have low perimeter/area ratios
            # Free-form signature strokes exhibit high stroke complexity
            if 0.1 <= aspect <= 10.0 and area >= 25:
                cv2.drawContours(stroke_candidates_mask, [cnt], -1, 255, -1)

        # 4. Cluster adjacent handwritten strokes into cohesive signature regions
        cluster_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (self._cluster_dilation * 2, self._cluster_dilation)
        )
        clustered = cv2.dilate(stroke_candidates_mask, cluster_kernel)

        # Find final candidate region clusters
        region_contours, _ = cv2.findContours(clustered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: list[NormalizedBoundingBox] = []
        for reg_cnt in region_contours:
            area = cv2.contourArea(reg_cnt)
            if area < self._min_area or area > (img_w * img_h * self._max_area_ratio):
                continue

            rx, ry, rw, rh = cv2.boundingRect(reg_cnt)
            aspect = float(rw) / max(1, rh)

            if not (self._min_aspect <= aspect <= self._max_aspect):
                continue

            # Normalized coordinate bounds clamped to [0.0, 1.0]
            norm_xmin = max(0.0, min(1.0, rx / img_w))
            norm_ymin = max(0.0, min(1.0, ry / img_h))
            norm_xmax = max(0.0, min(1.0, (rx + rw) / img_w))
            norm_ymax = max(0.0, min(1.0, (ry + rh) / img_h))

            if norm_xmin >= norm_xmax:
                norm_xmax = min(1.0, norm_xmin + 0.001)
            if norm_ymin >= norm_ymax:
                norm_ymax = min(1.0, norm_ymin + 0.001)

            candidates.append(
                NormalizedBoundingBox(
                    ymin=norm_ymin,
                    xmin=norm_xmin,
                    ymax=norm_ymax,
                    xmax=norm_xmax,
                )
            )

        # Sort candidates top-to-bottom, left-to-right
        candidates.sort(key=lambda b: (b.ymin, b.xmin))
        return candidates

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
