"""Centralized Quality Thresholds and Rule Configurations.

Provides deterministic thresholds, scoring penalties, and boundary definitions
for all quality analyzers. All values are centralized and configurable.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class QualityThresholds:
    """Configurable thresholds for all quality analyzers."""

    # Image: Blur
    blur_laplacian_warning: float = 120.0
    blur_laplacian_critical: float = 40.0

    # Image: Resolution & Dimensions
    min_page_dimension_pixels: int = 800
    min_total_pixels: int = 800_000
    min_estimated_dpi: float = 130.0
    low_dpi_critical: float = 90.0

    # Image: Contrast
    min_rms_contrast: float = 28.0
    critical_rms_contrast: float = 14.0
    min_michelson_contrast: float = 0.30

    # Image: Noise
    max_noise_sigma: float = 20.0
    critical_noise_sigma: float = 35.0

    # Image: Illumination & Brightness
    min_illumination_uniformity: float = 0.40
    critical_illumination_uniformity: float = 0.20
    min_mean_brightness: float = 40.0
    max_mean_brightness: float = 245.0

    # Image: Orientation & Skew
    max_skew_angle_deg: float = 2.0
    critical_skew_angle_deg: float = 6.0

    # Image: Cut-off content
    cutoff_margin_fraction: float = 0.02
    min_boundary_touch_pixels: int = 12

    # Image: Blank page
    blank_pixel_variance_threshold: float = 15.0
    blank_edge_energy_threshold: float = 5.0

    # PDF Structural bounds (in points, 72 pt/inch)
    pdf_min_dimension_points: float = 200.0
    pdf_max_dimension_points: float = 2500.0

    # Text extraction quality
    text_min_chars_per_page: int = 25
    text_very_short_chars: int = 10
    text_max_symbol_ratio: float = 0.30
    text_max_whitespace_ratio: float = 0.45
    text_max_fragmented_word_ratio: float = 0.30
    text_min_density_cpi: float = 2.0
    text_cross_page_cv_threshold: float = 0.60  # Coefficient of variation across pages


@dataclass(frozen=True)
class ScoringConfig:
    """Deterministic score penalty weights and category thresholds."""

    # Default issue point deductions
    PENALTY_MAP: ClassVar[dict[str, float]] = {
        # PDF structural issues
        "PDF_CORRUPT": 100.0,
        "PDF_EMPTY": 100.0,
        "PDF_ENCRYPTED": 100.0,
        "PDF_UNREADABLE_PAGE": 70.0,
        "PDF_BLANK_PAGE": 30.0,
        "PDF_UNUSUAL_DIMENSIONS": 10.0,
        "PDF_MIXED_ORIENTATIONS": 8.0,
        # Image issues
        "IMG_BLUR_CRITICAL": 35.0,
        "IMG_BLUR_WARNING": 15.0,
        "IMG_LOW_RESOLUTION": 25.0,
        "IMG_CRITICAL_LOW_RES": 45.0,
        "IMG_POOR_CONTRAST": 20.0,
        "IMG_CRITICAL_LOW_CONTRAST": 40.0,
        "IMG_EXCESSIVE_NOISE": 18.0,
        "IMG_CRITICAL_NOISE": 35.0,
        "IMG_UNEVEN_ILLUMINATION": 15.0,
        "IMG_SEVERE_SHADOW": 28.0,
        "IMG_ROTATED": 20.0,
        "IMG_SKEWED": 12.0,
        "IMG_CRITICAL_SKEW": 25.0,
        "IMG_CUTOFF_CONTENT": 22.0,
        "IMG_BLANK_PAGE": 35.0,
        # Text extraction issues
        "TXT_EMPTY_EXTRACTION": 40.0,
        "TXT_VERY_SHORT": 25.0,
        "TXT_REPLACEMENT_CHARS": 20.0,
        "TXT_EXCESSIVE_SYMBOLS": 18.0,
        "TXT_UNUSUAL_WHITESPACE": 10.0,
        "TXT_FRAGMENTED_WORDS": 15.0,
        "TXT_LOW_DENSITY": 10.0,
        "TXT_INCONSISTENT_ACROSS_PAGES": 15.0,
    }

    # Category score bands
    SCORE_EXCELLENT_MIN: float = 90.0
    SCORE_GOOD_MIN: float = 75.0
    SCORE_ACCEPTABLE_MIN: float = 50.0
    SCORE_POOR_MIN: float = 25.0

    # Dampening factor when multiple correlated defects are present
    # (e.g., both blur and low-res)
    CORRELATED_DEFECT_DAMPING: float = 0.75


DEFAULT_THRESHOLDS = QualityThresholds()
DEFAULT_SCORING_CONFIG = ScoringConfig()
