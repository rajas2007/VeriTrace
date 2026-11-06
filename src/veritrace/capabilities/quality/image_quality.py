"""Image Quality Analyzer.

Performs explainable computer vision measurements on document page images:
- Blur detection (Laplacian variance, edge energy)
- Low resolution & estimated DPI
- Contrast (RMS, Michelson)
- High-frequency noise estimation
- Uneven illumination & shadow detection
- Skew angle & orientation detection
- Potentially cut-off content near borders
- Blank page detection
"""

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from veritrace.capabilities.quality.models import (
    ImageQualityMetrics,
    QualityDimension,
    QualityIssue,
    QualitySeverity,
)
from veritrace.capabilities.quality.rules import DEFAULT_THRESHOLDS, QualityThresholds


class ImageQualityAnalyzer:
    """Evaluates the visual and physical quality of document page images."""

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def analyze(
        self,
        image_input: str | Path | Image.Image | np.ndarray,
        page_number: int = 1,
    ) -> tuple[ImageQualityMetrics, list[QualityIssue]]:
        """Run complete image quality analysis on a page image.

        Args:
            image_input: File path, PIL Image, or numpy array (BGR, RGB, or Gray).
            page_number: 1-based page sequence number.

        Returns:
            Tuple of (ImageQualityMetrics, list of QualityIssue).
        """
        gray, color, orig_dims = self._load_image(image_input)
        height, width = gray.shape[:2]
        total_pixels = width * height

        issues: list[QualityIssue] = []

        # 1. Blank page detection
        is_blank, var_pixel, edge_energy = self._check_blank(gray)
        if is_blank:
            issues.append(
                QualityIssue(
                    code="IMG_BLANK_PAGE",
                    title="Blank Page Detected",
                    message="The page image contains virtually no graphical or textual content.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.95,
                    measured_value=round(var_pixel, 2),
                    threshold=self.thresholds.blank_pixel_variance_threshold,
                    page_number=page_number,
                    details={"variance": var_pixel, "edge_energy": edge_energy},
                )
            )

        # 2. Resolution & Dimensions
        est_dpi = self._estimate_dpi(width, height)
        res_issues = self._evaluate_resolution(width, height, total_pixels, est_dpi, page_number)
        issues.extend(res_issues)

        # 3. Blur & Sharpness
        laplacian_var = self._compute_laplacian_variance(gray)
        blur_issues = self._evaluate_blur(laplacian_var, is_blank, page_number)
        issues.extend(blur_issues)

        # 4. Contrast
        rms_contrast, michelson = self._compute_contrast(gray)
        contrast_issues = self._evaluate_contrast(rms_contrast, michelson, is_blank, page_number)
        issues.extend(contrast_issues)

        # 5. Noise estimation
        noise_sigma = self._estimate_noise(gray)
        noise_issues = self._evaluate_noise(noise_sigma, page_number)
        issues.extend(noise_issues)

        # 6. Illumination & Brightness
        mean_bright, std_bright, uniformity = self._compute_illumination(gray)
        illum_issues = self._evaluate_illumination(mean_bright, uniformity, is_blank, page_number)
        issues.extend(illum_issues)

        # 7. Orientation & Skew
        skew_angle = self._detect_skew(gray, is_blank)
        skew_issues = self._evaluate_skew(skew_angle, page_number)
        issues.extend(skew_issues)

        orientation = self._detect_orientation(gray, width, height, is_blank)
        if orientation != 0:
            issues.append(
                QualityIssue(
                    code="IMG_ROTATED",
                    title=f"Page Rotated by ~{orientation}°",
                    message=f"Page is rotated by {orientation}° relative to upright orientation.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.80,
                    measured_value=float(orientation),
                    threshold=0.0,
                    page_number=page_number,
                    details={"detected_rotation_degrees": orientation},
                )
            )

        # 8. Potentially Cut-off Content
        cutoff_touches = self._detect_cutoff_content(gray, is_blank)
        if cutoff_touches >= self.thresholds.min_boundary_touch_pixels:
            issues.append(
                QualityIssue(
                    code="IMG_CUTOFF_CONTENT",
                    title="Potentially Clipped or Cut-Off Content",
                    message=(
                        "Document content intersects outer page margins, risking truncated text."
                    ),
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.85,
                    measured_value=float(cutoff_touches),
                    threshold=float(self.thresholds.min_boundary_touch_pixels),
                    page_number=page_number,
                    details={"margin_touch_pixel_count": cutoff_touches},
                )
            )

        metrics = ImageQualityMetrics(
            width_pixels=width,
            height_pixels=height,
            total_pixels=total_pixels,
            estimated_dpi=round(est_dpi, 1) if est_dpi else None,
            laplacian_variance=round(laplacian_var, 2),
            edge_energy=round(edge_energy, 2),
            michelson_contrast=round(michelson, 3),
            rms_contrast=round(rms_contrast, 2),
            noise_sigma=round(noise_sigma, 2),
            brightness_mean=round(mean_bright, 2),
            brightness_std=round(std_bright, 2),
            illumination_uniformity=round(uniformity, 3),
            skew_angle_deg=round(skew_angle, 2),
            detected_orientation_deg=orientation,
            boundary_content_touches=cutoff_touches,
            is_blank=is_blank,
        )

        return metrics, issues

    def _load_image(
        self, image_input: str | Path | Image.Image | np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
        """Normalize any image input to grayscale and BGR numpy arrays."""
        if isinstance(image_input, (str, Path)):
            path_str = str(image_input)
            img = cv2.imread(path_str, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Failed to read image file from: {path_str}")
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return gray, img, (img.shape[1], img.shape[0])

        if isinstance(image_input, Image.Image):
            rgb = np.array(image_input.convert("RGB"))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            return gray, bgr, (image_input.width, image_input.height)

        if isinstance(image_input, np.ndarray):
            if image_input.ndim == 2:
                gray = image_input.astype(np.uint8)
                bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            elif image_input.ndim == 3 and image_input.shape[2] == 3:
                bgr = image_input.astype(np.uint8)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            elif image_input.ndim == 3 and image_input.shape[2] == 4:
                bgr = cv2.cvtColor(image_input.astype(np.uint8), cv2.COLOR_BGRA2BGR)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            else:
                raise ValueError(f"Unsupported image array shape: {image_input.shape}")
            return gray, bgr, (gray.shape[1], gray.shape[0])

        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    def _check_blank(self, gray: np.ndarray) -> tuple[bool, float, float]:
        """Check if image has near-zero variance and edge energy."""
        var_pixel = float(np.var(gray))
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_energy = float(np.mean(np.sqrt(sobelx**2 + sobely**2)))

        is_blank = (
            var_pixel < self.thresholds.blank_pixel_variance_threshold
            and edge_energy < self.thresholds.blank_edge_energy_threshold
        )
        return is_blank, var_pixel, edge_energy

    def _estimate_dpi(self, width: int, height: int) -> float:
        """Estimate DPI assuming standard A4 document dimensions (8.27 x 11.69 inches)."""
        short_side = min(width, height)
        long_side = max(width, height)
        dpi_w = short_side / 8.27
        dpi_h = long_side / 11.69
        return (dpi_w + dpi_h) / 2.0

    def _evaluate_resolution(
        self, width: int, height: int, total_pixels: int, est_dpi: float, page_number: int
    ) -> list[QualityIssue]:
        issues = []
        min_dim = min(width, height)

        if total_pixels < 400_000 or min_dim < 500 or est_dpi < self.thresholds.low_dpi_critical:
            issues.append(
                QualityIssue(
                    code="IMG_CRITICAL_LOW_RES",
                    title="Severely Low Resolution",
                    message=(
                        f"Resolution ({width}x{height}, ~{int(est_dpi)} DPI) is severely degraded. "
                        "OCR character recognition accuracy will be critically compromised."
                    ),
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.98,
                    measured_value=float(total_pixels),
                    threshold=float(self.thresholds.min_total_pixels),
                    page_number=page_number,
                    details={"width": width, "height": height, "estimated_dpi": round(est_dpi, 1)},
                )
            )
        elif (
            total_pixels < self.thresholds.min_total_pixels
            or min_dim < self.thresholds.min_page_dimension_pixels
            or est_dpi < self.thresholds.min_estimated_dpi
        ):
            issues.append(
                QualityIssue(
                    code="IMG_LOW_RESOLUTION",
                    title="Low Image Resolution",
                    message=(
                        f"Page image ({width}x{height}, ~{int(est_dpi)} DPI) is below "
                        "the recommended 150 DPI baseline for reliable OCR."
                    ),
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.90,
                    measured_value=float(total_pixels),
                    threshold=float(self.thresholds.min_total_pixels),
                    page_number=page_number,
                    details={"width": width, "height": height, "estimated_dpi": round(est_dpi, 1)},
                )
            )
        return issues

    def _compute_laplacian_variance(self, gray: np.ndarray) -> float:
        """Compute the variance of Laplacian as a standard focus measure."""
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(np.var(lap))

    def _evaluate_blur(
        self, lap_var: float, is_blank: bool, page_number: int
    ) -> list[QualityIssue]:
        if is_blank:
            return []
        issues = []
        if lap_var < self.thresholds.blur_laplacian_critical:
            issues.append(
                QualityIssue(
                    code="IMG_BLUR_CRITICAL",
                    title="Severe Image Blur",
                    message=(
                        "Document exhibits critical optical defocus or motion blur, "
                        "preventing reliable text segmentation."
                    ),
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.95,
                    measured_value=round(lap_var, 2),
                    threshold=self.thresholds.blur_laplacian_critical,
                    page_number=page_number,
                    details={"laplacian_variance": round(lap_var, 2)},
                )
            )
        elif lap_var < self.thresholds.blur_laplacian_warning:
            issues.append(
                QualityIssue(
                    code="IMG_BLUR_WARNING",
                    title="Moderate Image Blur",
                    message=(
                        "Page image focus is soft; small fonts and fine numbers "
                        "may suffer character recognition errors."
                    ),
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.88,
                    measured_value=round(lap_var, 2),
                    threshold=self.thresholds.blur_laplacian_warning,
                    page_number=page_number,
                    details={"laplacian_variance": round(lap_var, 2)},
                )
            )
        return issues

    def _compute_contrast(self, gray: np.ndarray) -> tuple[float, float]:
        """Compute document foreground-background contrast and dynamic range."""
        thresh, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        fg_pixels = gray[bin_img == 0]
        bg_pixels = gray[bin_img == 255]

        if fg_pixels.size == 0 or bg_pixels.size == 0:
            p5, p95 = np.percentile(gray, [5, 95])
            denom = p95 + p5
            michelson = float((p95 - p5) / denom) if denom > 0 else 0.0
            rms = float(np.std(gray))
            return rms, michelson

        fg_mean = float(np.mean(fg_pixels))
        bg_mean = float(np.mean(bg_pixels))
        contrast_range = abs(bg_mean - fg_mean)
        denom = bg_mean + fg_mean
        michelson = float(contrast_range / denom) if denom > 0 else 0.0
        return contrast_range, michelson

    def _evaluate_contrast(
        self, rms: float, michelson: float, is_blank: bool, page_number: int
    ) -> list[QualityIssue]:
        if is_blank:
            return []
        issues = []
        if rms < self.thresholds.critical_rms_contrast or michelson < 0.15:
            issues.append(
                QualityIssue(
                    code="IMG_CRITICAL_LOW_CONTRAST",
                    title="Critically Low Contrast",
                    message="Text intensity is barely distinguishable from background paper.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.92,
                    measured_value=round(rms, 2),
                    threshold=self.thresholds.critical_rms_contrast,
                    page_number=page_number,
                    details={
                        "rms_contrast": round(rms, 2),
                        "michelson_contrast": round(michelson, 3),
                    },
                )
            )
        elif (
            rms < self.thresholds.min_rms_contrast
            or michelson < self.thresholds.min_michelson_contrast
        ):
            issues.append(
                QualityIssue(
                    code="IMG_POOR_CONTRAST",
                    title="Sub-optimal Contrast",
                    message="Low dynamic range between text and background may degrade OCR.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.85,
                    measured_value=round(rms, 2),
                    threshold=self.thresholds.min_rms_contrast,
                    page_number=page_number,
                    details={
                        "rms_contrast": round(rms, 2),
                        "michelson_contrast": round(michelson, 3),
                    },
                )
            )
        return issues

    def _estimate_noise(self, gray: np.ndarray) -> float:
        """Estimate additive high-frequency noise using residual standard deviation."""
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        diff = gray.astype(np.float32) - blurred.astype(np.float32)
        return float(np.std(diff))

    def _evaluate_noise(self, noise_sigma: float, page_number: int) -> list[QualityIssue]:
        issues = []
        if noise_sigma > self.thresholds.critical_noise_sigma:
            issues.append(
                QualityIssue(
                    code="IMG_CRITICAL_NOISE",
                    title="Severe Sensor / Compression Noise",
                    message="High noise amplitude detected; artifacts risk character degradation.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.90,
                    measured_value=round(noise_sigma, 2),
                    threshold=self.thresholds.critical_noise_sigma,
                    page_number=page_number,
                    details={"noise_sigma": round(noise_sigma, 2)},
                )
            )
        elif noise_sigma > self.thresholds.max_noise_sigma:
            issues.append(
                QualityIssue(
                    code="IMG_EXCESSIVE_NOISE",
                    title="Elevated Visual Noise",
                    message="Elevated background grain or salt-and-pepper noise observed.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.LOW,
                    confidence=0.80,
                    measured_value=round(noise_sigma, 2),
                    threshold=self.thresholds.max_noise_sigma,
                    page_number=page_number,
                    details={"noise_sigma": round(noise_sigma, 2)},
                )
            )
        return issues

    def _compute_illumination(self, gray: np.ndarray) -> tuple[float, float, float]:
        """Compute luminance distribution across a 4x4 spatial grid."""
        h, w = gray.shape
        mean_bright = float(np.mean(gray))
        std_bright = float(np.std(gray))

        grid_rows, grid_cols = 4, 4
        block_h = max(1, h // grid_rows)
        block_w = max(1, w // grid_cols)

        block_means = []
        for r in range(grid_rows):
            for c in range(grid_cols):
                y1 = r * block_h
                y2 = h if r == grid_rows - 1 else (r + 1) * block_h
                x1 = c * block_w
                x2 = w if c == grid_cols - 1 else (c + 1) * block_w
                block = gray[y1:y2, x1:x2]
                if block.size > 0:
                    block_means.append(float(np.mean(block)))

        if not block_means:
            return mean_bright, std_bright, 1.0

        min_m = min(block_means)
        max_m = max(block_means)
        uniformity = float(min_m / (max_m + 1e-5))
        return mean_bright, std_bright, uniformity

    def _evaluate_illumination(
        self, mean_bright: float, uniformity: float, is_blank: bool, page_number: int
    ) -> list[QualityIssue]:
        if is_blank:
            return []
        issues = []
        if uniformity < self.thresholds.critical_illumination_uniformity:
            issues.append(
                QualityIssue(
                    code="IMG_SEVERE_SHADOW",
                    title="Severe Non-uniform Illumination / Heavy Shadows",
                    message="Large spatial gradient or harsh shadow covers parts of the page.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.92,
                    measured_value=round(uniformity, 3),
                    threshold=self.thresholds.critical_illumination_uniformity,
                    page_number=page_number,
                    details={
                        "illumination_uniformity": round(uniformity, 3),
                        "mean_brightness": round(mean_bright, 2),
                    },
                )
            )
        elif uniformity < self.thresholds.min_illumination_uniformity:
            issues.append(
                QualityIssue(
                    code="IMG_UNEVEN_ILLUMINATION",
                    title="Uneven Illumination or Vignetting",
                    message="Noticeable lighting falloff or localized shadows detected.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.85,
                    measured_value=round(uniformity, 3),
                    threshold=self.thresholds.min_illumination_uniformity,
                    page_number=page_number,
                    details={
                        "illumination_uniformity": round(uniformity, 3),
                        "mean_brightness": round(mean_bright, 2),
                    },
                )
            )
        return issues

    def _detect_skew(self, gray: np.ndarray, is_blank: bool) -> float:
        """Estimate page skew angle using Hough line transform and projection profile."""
        if is_blank:
            return 0.0

        h, w = gray.shape
        if max(h, w) > 1600:
            scale = 1600.0 / max(h, w)
            proc_img = cv2.resize(
                gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
        else:
            proc_img = gray

        edges = cv2.Canny(proc_img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=80, maxLineGap=10
        )

        angles = []
        if lines is not None:
            for line in lines:
                coords = line.reshape(-1)
                if len(coords) >= 4:
                    x1, y1, x2, y2 = coords[:4]
                    dx = x2 - x1
                    dy = y2 - y1
                    if abs(dx) > abs(dy):
                        angle = math.degrees(math.atan2(dy, dx))
                        if -45.0 < angle < 45.0:
                            angles.append(angle)

        if len(angles) >= 5:
            return float(np.median(angles))

        # Fallback: projection profile variance across small angle window [-5, 5]
        best_angle = 0.0
        max_var = -1.0
        for angle_candidate in np.arange(-5.0, 5.5, 0.5):
            rot_mat = cv2.getRotationMatrix2D(
                (proc_img.shape[1] / 2, proc_img.shape[0] / 2), angle_candidate, 1.0
            )
            rotated = cv2.warpAffine(
                proc_img,
                rot_mat,
                (proc_img.shape[1], proc_img.shape[0]),
                flags=cv2.INTER_NEAREST,
            )
            profile = np.sum(rotated, axis=1)
            var_p = float(np.var(profile))
            if var_p > max_var:
                max_var = var_p
                best_angle = float(angle_candidate)

        return best_angle

    def _evaluate_skew(self, skew_angle: float, page_number: int) -> list[QualityIssue]:
        abs_skew = abs(skew_angle)
        issues = []
        if abs_skew > self.thresholds.critical_skew_angle_deg:
            issues.append(
                QualityIssue(
                    code="IMG_CRITICAL_SKEW",
                    title=f"Severe Document Skew ({skew_angle:+.1f}°)",
                    message="Document is significantly skewed, disrupting table/line alignment.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.HIGH,
                    confidence=0.90,
                    measured_value=round(skew_angle, 2),
                    threshold=self.thresholds.critical_skew_angle_deg,
                    page_number=page_number,
                    details={"skew_angle_degrees": round(skew_angle, 2)},
                )
            )
        elif abs_skew > self.thresholds.max_skew_angle_deg:
            issues.append(
                QualityIssue(
                    code="IMG_SKEWED",
                    title=f"Document Skew ({skew_angle:+.1f}°)",
                    message="Document text lines are tilted; deskewing is recommended.",
                    dimension=QualityDimension.IMAGE,
                    severity=QualitySeverity.LOW,
                    confidence=0.85,
                    measured_value=round(skew_angle, 2),
                    threshold=self.thresholds.max_skew_angle_deg,
                    page_number=page_number,
                    details={"skew_angle_degrees": round(skew_angle, 2)},
                )
            )
        return issues

    def _detect_orientation(self, gray: np.ndarray, width: int, height: int, is_blank: bool) -> int:
        """Detect whether a page is oriented upright (0) or rotated (90/180/270)."""
        if is_blank:
            return 0

        sobelx = np.abs(cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3))
        sobely = np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3))

        mean_x = float(np.mean(sobelx))
        mean_y = float(np.mean(sobely))

        if width > height * 1.25 and mean_x > mean_y * 1.35:
            return 90

        return 0

    def _detect_cutoff_content(self, gray: np.ndarray, is_blank: bool) -> int:
        """Count foreground content pixels intersecting the outer page border margins."""
        if is_blank:
            return 0

        h, w = gray.shape
        margin_x = max(4, int(w * self.thresholds.cutoff_margin_fraction))
        margin_y = max(4, int(h * self.thresholds.cutoff_margin_fraction))

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        top_band = binary[0:margin_y, :]
        bottom_band = binary[h - margin_y : h, :]
        left_band = binary[:, 0:margin_x]
        right_band = binary[:, w - margin_x : w]

        touches = 0
        touches += int(np.sum(top_band[0:2, :] > 0))
        touches += int(np.sum(bottom_band[-2:, :] > 0))
        touches += int(np.sum(left_band[:, 0:2] > 0))
        touches += int(np.sum(right_band[:, -2:] > 0))

        return touches
