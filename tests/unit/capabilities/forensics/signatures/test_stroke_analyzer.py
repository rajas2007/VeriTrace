"""Unit tests for SignatureStrokeAnalyzer stroke morphology and clipping detection."""

import cv2
import numpy as np

from veritrace.capabilities.forensics.signatures.stroke_analyzer import SignatureStrokeAnalyzer
from veritrace.domain.value_objects.forensic import SignatureEstimate, SignatureMeasurement
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


def create_natural_signature_crop() -> np.ndarray:
    """Create a 150x300 signature crop with natural handwriting strokes staying inside bounds."""
    crop = np.full((150, 300, 3), 255, dtype=np.uint8)
    # Natural signature drawn well inside perimeter
    pts = [
        (30, 80),
        (60, 40),
        (90, 110),
        (130, 50),
        (170, 95),
        (210, 60),
        (260, 100),
    ]
    for i in range(len(pts) - 1):
        cv2.line(crop, pts[i], pts[i + 1], (0, 0, 0), thickness=4)
    # Underline flourish staying inside
    cv2.ellipse(crop, (150, 120), (100, 20), 0, 0, 180, (0, 0, 0), thickness=3)
    return crop


def create_clipped_signature_crop() -> np.ndarray:
    """Create a signature crop that was digitally sliced abruptly through the outer boundary."""
    crop = np.full((150, 300, 3), 255, dtype=np.uint8)
    # Fill border edge with dark pixels simulating rectangular cut-and-paste artifact
    crop[0, 20:280] = 0
    crop[149, 20:280] = 0
    crop[10:140, 0] = 0
    crop[10:140, 299] = 0
    # Add some strokes inside
    cv2.line(crop, (0, 50), (299, 100), (0, 0, 0), thickness=6)
    return crop


def test_natural_signature_stroke_measurements():
    """Verify stroke analyzer measures stroke width, coverage, and low discontinuity."""
    crop = create_natural_signature_crop()
    analyzer = SignatureStrokeAnalyzer()
    bbox = NormalizedBoundingBox(ymin=0.6, xmin=0.5, ymax=0.75, xmax=0.8)

    measurement, estimate = analyzer.analyze_crop(crop, bbox)

    assert isinstance(measurement, SignatureMeasurement)
    assert isinstance(estimate, SignatureEstimate)

    # Stroke thickness ~4px
    assert 1.0 <= measurement.apparent_stroke_width_mean_px <= 10.0
    assert measurement.apparent_stroke_width_variance_px >= 0.0

    # Coverage should be reasonable (e.g. 2% to 25%)
    assert 1.0 <= measurement.stroke_pixel_coverage_pct <= 30.0

    # Natural signature should have very low boundary discontinuity (near 0)
    assert measurement.boundary_mask_discontinuity < 0.15

    # Apparent smoothness in [0.0, 1.0]
    assert 0.0 <= estimate.apparent_stroke_smoothness <= 1.0


def test_clipped_signature_boundary_discontinuity():
    """Verify stroke analyzer detects high boundary discontinuity on sliced rectangular masks."""
    crop = create_clipped_signature_crop()
    analyzer = SignatureStrokeAnalyzer()
    bbox = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.2, xmax=0.3)

    measurement, estimate = analyzer.analyze_crop(crop, bbox)

    # Should detect high boundary mask discontinuity
    assert measurement.boundary_mask_discontinuity > 0.40
