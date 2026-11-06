"""Unit tests for Image Quality Analyzer.

Tests all explainable image-level quality detectors:
- High quality image
- Blur detection (variance of Laplacian)
- Low resolution and estimated DPI
- Poor contrast (RMS and Michelson)
- High-frequency noise estimation
- Uneven brightness / illumination shadows
- Skew angle detection
- Rotated page detection
- Potentially cut-off / cropped content
- Blank canvas detection
"""

import numpy as np
import pytest

from tests.fixtures.quality.generators import (
    create_blank_image,
    create_blurry_image,
    create_clean_document_image,
    create_cutoff_image,
    create_low_contrast_image,
    create_low_res_image,
    create_noisy_image,
    create_skewed_image,
    create_uneven_illumination_image,
)
from veritrace.capabilities.quality.image_quality import ImageQualityAnalyzer
from veritrace.capabilities.quality.models import QualityDimension, QualitySeverity


@pytest.fixture
def analyzer() -> ImageQualityAnalyzer:
    return ImageQualityAnalyzer()


@pytest.fixture
def clean_image() -> np.ndarray:
    return create_clean_document_image(width=1200, height=1600)


def test_clean_image_quality(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that a clean synthetic document image has no high-severity quality issues."""
    metrics, issues = analyzer.analyze(clean_image, page_number=1)

    assert metrics.width_pixels == 1200
    assert metrics.height_pixels == 1600
    assert metrics.total_pixels == 1200 * 1600
    assert metrics.estimated_dpi is not None
    assert metrics.estimated_dpi >= 130.0
    assert metrics.is_blank is False
    assert metrics.laplacian_variance > 100.0

    critical_or_high = [
        i for i in issues if i.severity in (QualitySeverity.CRITICAL, QualitySeverity.HIGH)
    ]
    assert len(critical_or_high) == 0


def test_blur_detection(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that optical defocus blur is detected with variance of Laplacian measurement."""
    blurry = create_blurry_image(clean_image, ksize=31)
    metrics, issues = analyzer.analyze(blurry, page_number=1)

    assert metrics.laplacian_variance < 100.0
    blur_issues = [i for i in issues if "BLUR" in i.code]
    assert len(blur_issues) > 0

    issue = blur_issues[0]
    assert issue.dimension == QualityDimension.IMAGE
    assert issue.measured_value is not None
    assert issue.measured_value < 100.0
    assert issue.threshold is not None


def test_low_resolution_detection(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that downscaled images trigger low resolution warnings."""
    low_res = create_low_res_image(clean_image, target_dim=250)
    metrics, issues = analyzer.analyze(low_res, page_number=1)

    assert metrics.total_pixels < 400_000
    res_issues = [i for i in issues if "LOW_RES" in i.code or "RESOLUTION" in i.code]
    assert len(res_issues) > 0
    assert res_issues[0].severity in (QualitySeverity.HIGH, QualitySeverity.MEDIUM)


def test_poor_contrast_detection(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that compressed dynamic range triggers contrast defect."""
    low_contrast = create_low_contrast_image(clean_image)
    metrics, issues = analyzer.analyze(low_contrast, page_number=1)

    assert metrics.rms_contrast < 28.0
    contrast_issues = [i for i in issues if "CONTRAST" in i.code]
    assert len(contrast_issues) > 0


def test_noise_detection(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that elevated noise sigma is measured and flagged."""
    noisy = create_noisy_image(clean_image, sigma=60.0)
    metrics, issues = analyzer.analyze(noisy, page_number=1)

    assert metrics.noise_sigma > 20.0
    noise_issues = [i for i in issues if "NOISE" in i.code]
    assert len(noise_issues) > 0


def test_uneven_illumination_detection(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that harsh spatial lighting gradients are detected."""
    shadowed = create_uneven_illumination_image(clean_image)
    metrics, issues = analyzer.analyze(shadowed, page_number=1)

    assert metrics.illumination_uniformity < 0.45
    illum_issues = [i for i in issues if "ILLUMINATION" in i.code or "SHADOW" in i.code]
    assert len(illum_issues) > 0


def test_skew_detection(analyzer: ImageQualityAnalyzer, clean_image: np.ndarray):
    """Verify that tilted document page skew angle is measured."""
    skewed = create_skewed_image(clean_image, angle_deg=4.5)
    metrics, issues = analyzer.analyze(skewed, page_number=1)

    assert abs(metrics.skew_angle_deg) > 2.0
    skew_issues = [i for i in issues if "SKEW" in i.code]
    assert len(skew_issues) > 0


def test_cut_off_content_detection(analyzer: ImageQualityAnalyzer):
    """Verify that foreground text intersecting outer boundaries is flagged."""
    cutoff_img = create_cutoff_image(width=1200, height=1600)
    metrics, issues = analyzer.analyze(cutoff_img, page_number=1)

    assert metrics.boundary_content_touches >= 12
    cutoff_issues = [i for i in issues if i.code == "IMG_CUTOFF_CONTENT"]
    assert len(cutoff_issues) == 1
    assert cutoff_issues[0].severity == QualitySeverity.MEDIUM


def test_blank_page_detection(analyzer: ImageQualityAnalyzer):
    """Verify that completely blank images are flagged as IMG_BLANK_PAGE."""
    blank = create_blank_image(width=1200, height=1600)
    metrics, issues = analyzer.analyze(blank, page_number=1)

    assert metrics.is_blank is True
    blank_issues = [i for i in issues if i.code == "IMG_BLANK_PAGE"]
    assert len(blank_issues) == 1
    assert blank_issues[0].severity == QualitySeverity.HIGH


def test_image_input_types(analyzer: ImageQualityAnalyzer, tmp_path, clean_image: np.ndarray):
    """Verify that PIL Image, numpy array, and file paths are all accepted identically."""
    import cv2
    from PIL import Image

    # 1. Numpy array
    m1, i1 = analyzer.analyze(clean_image)

    # 2. PIL Image
    pil_img = Image.fromarray(cv2.cvtColor(clean_image, cv2.COLOR_BGR2RGB))
    m2, i2 = analyzer.analyze(pil_img)

    # 3. File path
    file_path = tmp_path / "test_doc.png"
    cv2.imwrite(str(file_path), clean_image)
    m3, i3 = analyzer.analyze(file_path)

    assert m1.width_pixels == m2.width_pixels == m3.width_pixels == 1200
    assert m1.height_pixels == m2.height_pixels == m3.height_pixels == 1600
