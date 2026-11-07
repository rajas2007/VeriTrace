"""Unit tests for Siamese Neural ONNX Signature Engine and Verifier Integration."""

from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.signatures.onnx_engine import (
    SiameseOnnxSignatureEngine,
)
from veritrace.capabilities.forensics.signatures.verifier import SignatureVerifier
from veritrace.domain.enums.forensic import SignatureAssessmentLevel
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


def create_test_signature_crop() -> np.ndarray:
    """Create reproducible synthetic stroke crop."""
    crop = np.full((120, 240, 3), 255, dtype=np.uint8)
    pts = [(30, 60), (70, 30), (100, 90), (140, 40), (180, 80), (220, 50)]
    for i in range(len(pts) - 1):
        cv2.line(crop, pts[i], pts[i + 1], (0, 0, 0), thickness=3)
    cv2.ellipse(crop, (140, 85), (80, 15), 0, 0, 180, (0, 0, 0), thickness=2)
    return crop


def test_onnx_engine_unavailability_when_model_missing():
    """Verify engine reports unavailable when model path does not exist."""
    engine = SiameseOnnxSignatureEngine(model_path=Path("non_existent_siamese.onnx"))
    assert engine.is_available() is False

    dummy_crop = np.full((100, 100), 255, dtype=np.uint8)
    with pytest.raises(RuntimeError, match="Siamese ONNX signature engine is unavailable"):
        engine.compute_metric_distance(dummy_crop, dummy_crop)


def test_onnx_engine_crop_preprocessing():
    """Verify input crop is resized, grayscale-converted, and normalized."""
    engine = SiameseOnnxSignatureEngine(model_path=Path("non_existent.onnx"))

    # Test with color image
    color_crop = np.full((80, 160, 3), 200, dtype=np.uint8)
    processed = engine.preprocess_crop(color_crop)

    assert processed.shape == (1, 1, 128, 128)
    assert processed.dtype == np.float32
    assert 0.0 <= processed.min() <= processed.max() <= 1.0


def test_onnx_engine_metric_distance_calculation():
    """Verify cosine metric distance computation logic."""
    engine = SiameseOnnxSignatureEngine(model_path=Path("non_existent.onnx"))

    mock_session = MagicMock()
    engine._session = mock_session
    engine._input_name = "input"

    # Identical vectors -> distance 0.0
    v1 = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    mock_session.run.side_effect = [[v1], [v1]]
    dummy_crop = np.full((100, 100), 255, dtype=np.uint8)
    dist = engine.compute_metric_distance(dummy_crop, dummy_crop)
    assert abs(dist - 0.0) < 1e-5

    # Orthogonal vectors -> distance 0.5
    v2 = np.array([[0.0, 1.0, 0.0]], dtype=np.float32)
    mock_session.run.side_effect = [[v1], [v2]]
    dist = engine.compute_metric_distance(dummy_crop, dummy_crop)
    assert abs(dist - 0.5) < 1e-5

    # Opposite vectors -> distance 1.0
    v3 = np.array([[-1.0, 0.0, 0.0]], dtype=np.float32)
    mock_session.run.side_effect = [[v1], [v3]]
    dist = engine.compute_metric_distance(dummy_crop, dummy_crop)
    assert abs(dist - 1.0) < 1e-5


def test_onnx_engine_with_mock_session():
    """Verify ONNX inference flow when session returns valid embeddings."""
    engine = SiameseOnnxSignatureEngine(model_path=Path("dummy.onnx"))

    # Create mock session
    mock_session = MagicMock()
    # Return 128-d unit vector
    dummy_emb = np.zeros((1, 128), dtype=np.float32)
    dummy_emb[0, 0] = 1.0
    mock_session.run.return_value = [dummy_emb]

    engine._session = mock_session
    engine._input_name = "input"
    assert engine.is_available() is True

    crop1 = create_test_signature_crop()
    crop2 = create_test_signature_crop()

    dist = engine.compute_metric_distance(crop1, crop2)
    assert abs(dist - 0.0) < 1e-5
    assert mock_session.run.call_count == 2


def test_signature_verifier_neural_onnx_integration():
    """Verify SignatureVerifier delegates to ONNX engine and maps epistemic level."""
    mock_engine = MagicMock(spec=SiameseOnnxSignatureEngine)
    mock_engine.is_available.return_value = True
    # Simulate high similarity
    mock_engine.compute_metric_distance.return_value = 0.12

    verifier = SignatureVerifier(
        onnx_engine=mock_engine,
        distance_threshold_match=0.30,
        distance_threshold_anomaly=0.55,
    )

    q_crop = create_test_signature_crop()
    ref_crop = create_test_signature_crop()

    result = verifier.verify_against_reference(
        questioned_crop=q_crop,
        reference_profile_or_crop=ref_crop,
        normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.5),
    )

    mock_engine.compute_metric_distance.assert_called_once()
    assert result.assessment == SignatureAssessmentLevel.SIMILARITY_WITH_REFERENCE
    assert result.estimate.metric_embedding_distance == 0.12


def test_signature_verifier_fallback_on_neural_exception():
    """Verify graceful fallback to classical heuristics when ONNX inference raises."""
    mock_engine = MagicMock(spec=SiameseOnnxSignatureEngine)
    mock_engine.is_available.return_value = True
    mock_engine.compute_metric_distance.side_effect = RuntimeError("ONNX execution error")

    verifier = SignatureVerifier(onnx_engine=mock_engine)

    q_crop = create_test_signature_crop()
    ref_crop = create_test_signature_crop()

    # Should not raise; should gracefully fall back to classical heuristics
    result = verifier.verify_against_reference(
        questioned_crop=q_crop,
        reference_profile_or_crop=ref_crop,
        normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.5),
    )

    assert result.assessment is not None
    assert result.estimate.metric_embedding_distance is not None
