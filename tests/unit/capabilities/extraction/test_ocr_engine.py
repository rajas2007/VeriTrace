"""Unit tests for TesseractOcrEngine and OCR fallback handling."""

from unittest.mock import patch

import numpy as np

from veritrace.capabilities.extraction.ocr_engine import (
    OcrPageResult,
    TesseractOcrEngine,
)
from veritrace.domain.enums.document import ExtractionSourceType


def test_tesseract_ocr_engine_initialization():
    """Verify initialization and custom command path."""
    engine = TesseractOcrEngine(tesseract_cmd="custom_tesseract")
    assert engine._tesseract_cmd == "custom_tesseract"


def test_preprocess_image():
    """Verify CLAHE contrast preprocessing produces valid single-channel image."""
    engine = TesseractOcrEngine()
    # 3-channel dummy image
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    processed = engine.preprocess_image(img)

    assert processed.shape == (100, 100)
    assert processed.dtype == np.uint8


def test_extract_page_ocr_unavailable_fallback():
    """Verify that unavailable Tesseract returns diagnostic warning without crashing."""
    engine = TesseractOcrEngine()
    # Mock is_available to return False
    with patch.object(engine, "is_available", return_value=False):
        dummy_img = np.zeros((200, 300, 3), dtype=np.uint8)
        result = engine.extract_page_ocr(dummy_img, page_number=1)

        assert isinstance(result, OcrPageResult)
        assert result.page_number == 1
        assert len(result.tokens) == 0
        assert len(result.warnings) > 0
        assert "not available" in result.warnings[0].lower()


def test_extract_page_ocr_mock_success():
    """Verify token generation, bounding boxes, and confidence mapping with mock pytesseract."""
    engine = TesseractOcrEngine()

    mock_data = {
        "text": ["", "INVOICE", "TOTAL", "85000"],
        "conf": [-1, 95.0, 92.0, 88.0],
        "left": [0, 50, 150, 250],
        "top": [0, 10, 10, 10],
        "width": [0, 80, 80, 60],
        "height": [0, 30, 30, 30],
    }

    dummy_img = np.zeros((400, 600, 3), dtype=np.uint8)

    with (
        patch.object(engine, "is_available", return_value=True),
        patch("pytesseract.image_to_data", return_value=mock_data),
        patch.object(engine, "get_version", return_value="5.3.0"),
    ):
        result = engine.extract_page_ocr(dummy_img, page_number=1, lang="eng")

        assert len(result.tokens) == 3
        assert result.full_text == "INVOICE TOTAL 85000"
        assert result.mean_confidence > 0.85

        tok1 = result.tokens[0]
        assert tok1.raw_text == "INVOICE"
        assert tok1.confidence == 0.95
        assert tok1.source_type == ExtractionSourceType.OCR
        assert tok1.page_number == 1
        # Bounding box should be normalized in [0.0, 1.0]
        assert 0.0 <= tok1.normalized_bbox.ymin <= 1.0
        assert 0.0 <= tok1.normalized_bbox.xmin <= 1.0
        assert tok1.normalized_bbox.ymin < tok1.normalized_bbox.ymax
        assert tok1.normalized_bbox.xmin < tok1.normalized_bbox.xmax
