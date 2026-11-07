"""Unit tests for PaddleOcrEngine adapter and language routing."""

import numpy as np
import pytest

from veritrace.capabilities.extraction.ocr_engine import OcrPageResult
from veritrace.capabilities.extraction.paddle_ocr_engine import PaddleOcrEngine
from veritrace.domain.enums.document import ExtractionSourceType


def test_paddle_ocr_engine_fallback_when_unavailable():
    """Verify clean diagnostic OcrPageResult when PaddleOCR is not installed."""
    engine = PaddleOcrEngine()
    # Force unavailable state
    engine._custom_runner = None

    if not engine.is_available():
        dummy_img = np.zeros((300, 300, 3), dtype=np.uint8)
        res = engine.extract_page_ocr(dummy_img, page_number=1, lang="eng")

        assert isinstance(res, OcrPageResult)
        assert res.ocr_engine == "PaddleOCR"
        assert res.ocr_model_version == "unavailable"
        assert len(res.tokens) == 0
        assert len(res.warnings) > 0
        assert "not installed" in res.warnings[0].lower() or "bypassed" in res.warnings[0].lower()


def test_paddle_ocr_language_mapping():
    """Verify correct ISO 639-3 / BCP-47 mapping to PaddleOCR language codes."""
    engine = PaddleOcrEngine()
    assert engine._get_paddle_lang("eng") == "en"
    assert engine._get_paddle_lang("en") == "en"
    assert engine._get_paddle_lang("hin") == "hi"
    assert engine._get_paddle_lang("mar") == "hi"
    assert engine._get_paddle_lang("mr") == "hi"
    assert engine._get_paddle_lang("tam") == "ta"
    assert engine._get_paddle_lang("tel") == "te"
    assert engine._get_paddle_lang("unknown_lang") == "en"


def test_paddle_ocr_with_mock_runner():
    """Verify coordinate normalization, script detection, and token creation with runner."""

    # Mock runner returning standard PaddleOCR line structure:
    # [ [ [box_coords], (text, confidence) ], ... ]
    def mock_runner(img: np.ndarray, lang: str):
        h, w = img.shape[:2]
        # Box from x=50 to 150, y=20 to 60
        box1 = [[50, 20], [150, 20], [150, 60], [50, 60]]
        # Devanagari word: "रुपये"
        box2 = [[200, 100], [350, 100], [350, 140], [200, 140]]
        return [
            [
                [box1, ("INVOICE", 0.98)],
                [box2, ("रुपये", 0.95)],
            ]
        ]

    engine = PaddleOcrEngine(ocr_runner=mock_runner)
    assert engine.is_available() is True

    canvas = np.ones((500, 1000, 3), dtype=np.uint8) * 255
    res = engine.extract_page_ocr(canvas, page_number=2, lang="hin")

    assert res.ocr_engine == "PaddleOCR"
    assert len(res.tokens) == 2
    assert res.page_number == 2

    # Verify first token: "INVOICE"
    tok1 = res.tokens[0]
    assert tok1.raw_text == "INVOICE"
    assert tok1.confidence == 0.98
    assert tok1.source_type == ExtractionSourceType.OCR
    assert tok1.script == "Latn"
    # BBox check: x in [50, 150] on w=1000 -> x in [0.05, 0.15]
    # y in [20, 60] on h=500 -> y in [0.04, 0.12]
    assert pytest.approx(tok1.normalized_bbox.xmin, abs=0.01) == 0.05
    assert pytest.approx(tok1.normalized_bbox.xmax, abs=0.01) == 0.15
    assert pytest.approx(tok1.normalized_bbox.ymin, abs=0.01) == 0.04
    assert pytest.approx(tok1.normalized_bbox.ymax, abs=0.01) == 0.12

    # Verify second token: "रुपये" (Devanagari script)
    tok2 = res.tokens[1]
    assert tok2.raw_text == "रुपये"
    assert tok2.confidence == 0.95
    assert tok2.script == "Deva"

    assert "INVOICE रुपये" in res.full_text
    assert res.mean_confidence == pytest.approx(0.965, abs=0.01)
