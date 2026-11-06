"""Unit tests for SignatureDetector contour and stroke localization."""

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.signatures.detector import SignatureDetector
from veritrace.domain.exceptions.base import ValidationError


def create_canvas_with_signature_and_stamps() -> np.ndarray:
    """Create synthetic document image with signature, guideline, and circular stamp."""
    canvas = np.full((1000, 1000, 3), 255, dtype=np.uint8)

    # 1. Horizontal guideline underline (should be ignored by stroke filter)
    cv2.line(canvas, (100, 750), (900, 750), (0, 0, 0), thickness=2)

    # 2. Circular official stamp at bottom left (should be ignored due to circularity > 0.72)
    cv2.circle(canvas, (300, 600), 50, (0, 0, 0), thickness=3)
    cv2.putText(canvas, "OFFICIAL", (265, 605), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # 3. Handwritten cursive signature strokes at (500, 650) to (750, 720)
    pts = [
        (520, 690),
        (540, 660),
        (560, 710),
        (590, 670),
        (620, 700),
        (650, 665),
        (690, 715),
        (730, 680),
    ]
    for i in range(len(pts) - 1):
        cv2.line(canvas, pts[i], pts[i + 1], (0, 0, 0), thickness=3)
    # Add a flourish curve
    cv2.ellipse(canvas, (620, 700), (90, 25), 10, 0, 180, (0, 0, 0), thickness=2)

    return canvas


def test_detector_finds_signature_and_ignores_stamp():
    """Verify SignatureDetector isolates signature while rejecting stamps and form lines."""
    canvas = create_canvas_with_signature_and_stamps()
    detector = SignatureDetector(min_area_px=200)

    candidates = detector.detect_candidate_regions(canvas)

    assert len(candidates) >= 1
    # Check that candidate overlaps with our signature coordinates (520-730, 660-720)
    # Normalized coords: x in [0.50, 0.75], y in [0.64, 0.74]
    sig_candidates = [c for c in candidates if 0.48 <= c.xmin <= 0.75 and 0.60 <= c.ymin <= 0.75]
    assert len(sig_candidates) >= 1
    detected_box = sig_candidates[0]
    assert detected_box.xmin < detected_box.xmax
    assert detected_box.ymin < detected_box.ymax

    # Check that circular stamp (center 300, 600 -> xmin~0.25, xmax~0.35) is not returned
    stamp_candidates = [c for c in candidates if 0.20 <= c.xmin <= 0.40 and 0.50 <= c.ymin <= 0.70]
    assert len(stamp_candidates) == 0


def test_detector_blank_page():
    """Verify empty canvas returns zero candidate regions."""
    blank = np.full((800, 800, 3), 255, dtype=np.uint8)
    detector = SignatureDetector()
    candidates = detector.detect_candidate_regions(blank)
    assert candidates == []


def test_detector_input_types(tmp_path):
    """Verify SignatureDetector accepts Path and byte buffers as inputs."""
    canvas = create_canvas_with_signature_and_stamps()
    img_path = tmp_path / "page_sig.png"
    cv2.imwrite(str(img_path), canvas)

    detector = SignatureDetector(min_area_px=200)

    # 1. Path input
    path_candidates = detector.detect_candidate_regions(img_path)
    assert len(path_candidates) >= 1

    # 2. Bytes input
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    bytes_candidates = detector.detect_candidate_regions(img_bytes)
    assert len(bytes_candidates) == len(path_candidates)

    # 3. Invalid path
    with pytest.raises(ValidationError):
        detector.detect_candidate_regions(tmp_path / "non_existent.png")
