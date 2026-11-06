"""Unit tests for CopyMoveDetector."""

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.copy_move import CopyMoveDetector
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


@pytest.fixture
def signature_stamp_patch() -> np.ndarray:
    """Generate a high-contrast synthetic stamp/signature pattern."""
    patch = np.full((150, 150, 3), 255, dtype=np.uint8)
    # Draw concentric circles and diagonal lines
    cv2.circle(patch, (75, 75), 60, (180, 20, 20), 3)
    cv2.circle(patch, (75, 75), 45, (180, 20, 20), 2)
    cv2.putText(patch, "OFFICIAL", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 20, 20), 2)
    cv2.putText(patch, "STAMP", (35, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 20, 20), 2)
    return patch


def test_match_identical_regions(signature_stamp_patch: np.ndarray):
    """Verify CopyMoveDetector identifies identical cloned stamps with high inliers."""
    detector = CopyMoveDetector(min_inlier_matches=10)

    # Identical patch
    crop1 = signature_stamp_patch.copy()
    crop2 = signature_stamp_patch.copy()

    bbox1 = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.3)
    bbox2 = NormalizedBoundingBox(ymin=0.6, xmin=0.6, ymax=0.8, xmax=0.8)

    match = detector.match_regions(
        source_crop=crop1,
        target_crop=crop2,
        source_page=1,
        source_bbox=bbox1,
        target_page=2,
        target_bbox=bbox2,
        match_type="STAMP",
    )

    assert match is not None
    assert match.inlier_match_count >= 10
    assert match.similarity_score > 0.6
    assert match.match_type == "STAMP"


def test_distinct_patches_do_not_match(signature_stamp_patch: np.ndarray):
    """Verify distinct random patches return None."""
    detector = CopyMoveDetector(min_inlier_matches=10)

    crop1 = signature_stamp_patch.copy()
    # Different patch: purely blank with simple cross
    crop2 = np.full((150, 150, 3), 255, dtype=np.uint8)
    cv2.line(crop2, (10, 10), (140, 140), (0, 0, 0), 2)

    bbox1 = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.3)
    bbox2 = NormalizedBoundingBox(ymin=0.6, xmin=0.6, ymax=0.8, xmax=0.8)

    match = detector.match_regions(
        source_crop=crop1,
        target_crop=crop2,
        source_page=1,
        source_bbox=bbox1,
        target_page=2,
        target_bbox=bbox2,
    )

    assert match is None
