"""Unit tests for SignatureCropQualityAssessor (Milestone 1.9 Part B)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.signatures.crop_quality import (
    SignatureCropQualityAssessor,
)
from veritrace.domain.exceptions.base import ValidationError


@pytest.fixture
def assessor() -> SignatureCropQualityAssessor:
    return SignatureCropQualityAssessor()


def test_missing_file_raises_validation_error(
    assessor: SignatureCropQualityAssessor, tmp_path: Path
) -> None:
    non_existent = tmp_path / "non_existent.png"
    with pytest.raises(ValidationError, match="not found"):
        assessor.evaluate(non_existent)


def test_tiny_crop_fails_adequacy(assessor: SignatureCropQualityAssessor, tmp_path: Path) -> None:
    tiny_img = np.ones((15, 40), dtype=np.uint8) * 255
    path = tmp_path / "tiny.png"
    cv2.imwrite(str(path), tiny_img)

    result = assessor.evaluate(path)
    assert not result.is_adequate
    assert any("Insufficient crop dimensions" in r for r in result.reasons)


def test_blank_crop_fails_adequacy(assessor: SignatureCropQualityAssessor, tmp_path: Path) -> None:
    blank_img = np.ones((100, 200), dtype=np.uint8) * 255
    path = tmp_path / "blank.png"
    cv2.imwrite(str(path), blank_img)

    result = assessor.evaluate(path)
    assert not result.is_adequate
    assert any("contrast" in r.lower() or "stroke" in r.lower() for r in result.reasons)


def test_blurred_crop_fails_adequacy(
    assessor: SignatureCropQualityAssessor, tmp_path: Path
) -> None:
    img = np.ones((120, 300), dtype=np.uint8) * 255
    # Draw simple stroke then apply heavy blur
    cv2.line(img, (20, 60), (280, 60), 0, 5)
    blurred = cv2.GaussianBlur(img, (45, 45), 15.0)
    path = tmp_path / "blurred.png"
    cv2.imwrite(str(path), blurred)

    result = assessor.evaluate(path)
    assert not result.is_adequate
    assert any("blur" in r.lower() for r in result.reasons)


def test_boundary_discontinuity_metric_calculated(
    assessor: SignatureCropQualityAssessor, tmp_path: Path
) -> None:
    # Signature stroke bleeding heavily right through edge border
    img = np.ones((100, 200), dtype=np.uint8) * 255
    # Draw dark strokes all along top border (y=0, 1, 2)
    img[0:3, 20:180] = 0
    path = tmp_path / "clipped.png"
    cv2.imwrite(str(path), img)

    result = assessor.evaluate(path)
    assert result.boundary_discontinuity > 0.0


def test_adequate_quality_signature_passes(
    assessor: SignatureCropQualityAssessor, tmp_path: Path
) -> None:
    # Create clean synthetic signature crop with white background, sharp dark strokes, centered
    img = np.ones((120, 300), dtype=np.uint8) * 255
    # Draw distinct curves safely inside margins
    cv2.ellipse(img, (100, 60), (60, 30), 20, 0, 360, 0, 2)
    cv2.line(img, (50, 70), (250, 50), 0, 2)
    cv2.line(img, (150, 30), (200, 90), 0, 2)
    cv2.circle(img, (220, 50), 6, 0, -1)

    path = tmp_path / "adequate_sig.png"
    cv2.imwrite(str(path), img)

    result = assessor.evaluate(path)
    assert result.is_adequate
    assert len(result.reasons) == 0
    assert result.blur_score > 35.0
    assert result.contrast_score > 15.0
    assert result.stroke_coverage_pct >= 0.20
