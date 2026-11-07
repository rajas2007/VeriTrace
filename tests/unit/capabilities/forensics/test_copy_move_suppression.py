"""Unit tests for CopyMoveDetector layout suppression (Milestone 1.9 Part C)."""

from __future__ import annotations

import cv2
import numpy as np

from veritrace.capabilities.forensics.copy_move import CopyMoveDetector
from veritrace.domain.entities.evidence import NormalizedBoundingBox


def test_header_logo_match_is_suppressed() -> None:
    source_bbox = NormalizedBoundingBox(ymin=0.02, xmin=0.1, ymax=0.12, xmax=0.4)
    target_bbox = NormalizedBoundingBox(ymin=0.03, xmin=0.1, ymax=0.14, xmax=0.42)

    is_suppressed, reason = CopyMoveDetector.evaluate_layout_suppression(source_bbox, target_bbox)
    assert is_suppressed is True
    assert reason is not None
    assert "recurring header margin" in reason
    assert "corporate letterhead" in reason


def test_footer_disclaimer_match_is_suppressed() -> None:
    source_bbox = NormalizedBoundingBox(ymin=0.88, xmin=0.05, ymax=0.98, xmax=0.95)
    target_bbox = NormalizedBoundingBox(ymin=0.87, xmin=0.05, ymax=0.97, xmax=0.95)

    is_suppressed, reason = CopyMoveDetector.evaluate_layout_suppression(source_bbox, target_bbox)
    assert is_suppressed is True
    assert reason is not None
    assert "recurring footer margin" in reason
    assert "pagination" in reason or "disclaimer" in reason


def test_body_content_match_is_not_suppressed() -> None:
    source_bbox = NormalizedBoundingBox(ymin=0.35, xmin=0.2, ymax=0.55, xmax=0.6)
    target_bbox = NormalizedBoundingBox(ymin=0.40, xmin=0.2, ymax=0.60, xmax=0.6)

    is_suppressed, reason = CopyMoveDetector.evaluate_layout_suppression(source_bbox, target_bbox)
    assert is_suppressed is False
    assert reason is None


def test_asymmetric_header_to_body_match_is_not_suppressed() -> None:
    source_bbox = NormalizedBoundingBox(ymin=0.05, xmin=0.1, ymax=0.15, xmax=0.4)
    target_bbox = NormalizedBoundingBox(ymin=0.50, xmin=0.1, ymax=0.60, xmax=0.4)

    is_suppressed, reason = CopyMoveDetector.evaluate_layout_suppression(source_bbox, target_bbox)
    assert is_suppressed is False
    assert reason is None


def test_match_regions_attaches_suppression_metadata() -> None:
    detector = CopyMoveDetector(min_inlier_matches=4)

    # Generate identical rich patterned patches
    crop = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(10, 90, 15):
        cv2.circle(crop, (i, i), 8, (255, 255, 255), -1)
        cv2.line(crop, (i, 10), (10, i), (200, 200, 200), 2)

    # Place in header margin
    hdr_box = NormalizedBoundingBox(ymin=0.02, xmin=0.05, ymax=0.15, xmax=0.25)

    match = detector.match_regions(
        source_crop=crop,
        target_crop=crop.copy(),
        source_page=1,
        source_bbox=hdr_box,
        target_page=2,
        target_bbox=hdr_box,
        match_type="HEADER",
    )

    assert match is not None
    assert match.is_suppressed is True
    assert match.suppression_reason is not None
    assert "header margin" in match.suppression_reason
