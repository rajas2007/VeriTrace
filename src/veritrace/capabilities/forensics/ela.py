"""Error Level Analysis (ELA) engine detecting compression discontinuities."""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from veritrace.capabilities.forensics.models import ELAResult
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


class ErrorLevelAnalyzer:
    """Detects compression discontinuities and digital splicing using Error Level Analysis."""

    def __init__(
        self,
        quality: int = 95,
        scale_factor: int = 15,
        anomaly_sigma_threshold: float = 3.0,
        min_region_area_px: int = 120,
    ) -> None:
        self._quality = quality
        self._scale_factor = scale_factor
        self._anomaly_sigma_threshold = anomaly_sigma_threshold
        self._min_region_area_px = min_region_area_px

    def compute_ela(
        self,
        image_or_path: np.ndarray | Path | bytes,
        output_heatmap_path: Path | None = None,
    ) -> ELAResult:
        """Execute Error Level Analysis on a document canvas.

        Args:
            image_or_path: OpenCV BGR array, Path, or raw image bytes.
            output_heatmap_path: Optional destination to save the colored ELA heatmap PNG.

        Returns:
            ELAResult containing statistical measurements, anomaly flag, and candidate boxes.
        """
        img_bgr = self._load_image(image_or_path)
        img_h, img_w = img_bgr.shape[:2]

        # 1. Resave image at controlled JPEG quality in memory
        pil_orig = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        buf = io.BytesIO()
        pil_orig.save(buf, format="JPEG", quality=self._quality)
        buf.seek(0)
        resaved_pil = Image.open(buf)
        resaved_bgr = cv2.cvtColor(np.array(resaved_pil), cv2.COLOR_RGB2BGR)

        # 2. Compute absolute pixel differential scaled by magnification factor
        # Cast to float32 to prevent underflow/overflow
        diff_f32 = np.abs(img_bgr.astype(np.float32) - resaved_bgr.astype(np.float32))
        diff_scaled = np.clip(diff_f32 * self._scale_factor, 0, 255).astype(np.uint8)

        # Convert to single-channel luminance difference for statistical analysis
        diff_gray = cv2.cvtColor(diff_scaled, cv2.COLOR_BGR2GRAY)

        # 3. Statistical measurements
        global_mean = float(np.mean(diff_gray))
        global_std = float(np.std(diff_gray))
        max_error = float(np.max(diff_gray))

        # 4. Detect localized anomaly regions (pixels exceeding mean + k * std)
        # Avoid division by zero on perfectly uniform synthetic images
        threshold_val = global_mean + self._anomaly_sigma_threshold * max(1.0, global_std)
        _, thresh_mask = cv2.threshold(diff_gray, threshold_val, 255, cv2.THRESH_BINARY)

        # Morphological closing to bridge adjacent compression error pixels in an inserted patch
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        connected_mask = cv2.morphologyEx(thresh_mask, cv2.MORPH_CLOSE, kernel)

        # Find connected components for candidate anomaly bounding boxes
        contours, _ = cv2.findContours(connected_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        anomalous_regions: list[NormalizedBoundingBox] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self._min_region_area_px:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            # Normalize to [ymin, xmin, ymax, xmax]
            norm_xmin = max(0.0, min(1.0, x / img_w))
            norm_ymin = max(0.0, min(1.0, y / img_h))
            norm_xmax = max(0.0, min(1.0, (x + w) / img_w))
            norm_ymax = max(0.0, min(1.0, (y + h) / img_h))

            if norm_xmin >= norm_xmax:
                norm_xmax = min(1.0, norm_xmin + 0.001)
            if norm_ymin >= norm_ymax:
                norm_ymax = min(1.0, norm_ymin + 0.001)

            anomalous_regions.append(
                NormalizedBoundingBox(
                    ymin=norm_ymin,
                    xmin=norm_xmin,
                    ymax=norm_ymax,
                    xmax=norm_xmax,
                )
            )

        # Calculate normalized anomaly score in [0.0, 1.0]
        # Ratio of max error and high-variance regions relative to background
        anomaly_detected = len(anomalous_regions) > 0
        if anomaly_detected:
            denom = self._anomaly_sigma_threshold * max(1.0, global_std) * 2.0
            anomaly_score = min(1.0, float((max_error - global_mean) / denom))
            anomaly_score = max(0.3, anomaly_score)
        else:
            anomaly_score = 0.0

        # 5. Generate and save heatmap if requested
        heatmap_path: Path | None = None
        if output_heatmap_path is not None:
            output_heatmap_path.parent.mkdir(parents=True, exist_ok=True)
            # Apply color map (JET: blue=low error, green=medium, red=high error)
            heatmap_bgr = cv2.applyColorMap(diff_gray, cv2.COLORMAP_JET)

            # Draw subtle rectangles around detected anomalies for forensic reviewer
            for reg in anomalous_regions:
                rx1, ry1, rx2, ry2 = reg.to_pixels(img_w, img_h)
                cv2.rectangle(heatmap_bgr, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)

            cv2.imwrite(str(output_heatmap_path), heatmap_bgr)
            heatmap_path = output_heatmap_path

        return ELAResult(
            global_mean_error=global_mean,
            global_std_error=global_std,
            max_local_error=max_error,
            anomaly_detected=anomaly_detected,
            anomaly_score=anomaly_score,
            heatmap_path=heatmap_path,
            anomalous_regions=anomalous_regions,
            quality_tested=self._quality,
            scale_factor=self._scale_factor,
        )

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
