"""Unit tests for OCR Engine Registry and fallback routing."""

from unittest.mock import MagicMock

from veritrace.capabilities.extraction.engine_registry import OcrEngineRegistry
from veritrace.capabilities.extraction.ocr_engine import (
    OcrEngineProtocol,
    TesseractOcrEngine,
)


def test_ocr_registry_default_tesseract():
    """Verify default engine is Tesseract."""
    registry = OcrEngineRegistry()
    engine = registry.get_engine(None)
    assert isinstance(engine, TesseractOcrEngine)

    engine_named = registry.get_engine("tesseract")
    assert isinstance(engine_named, TesseractOcrEngine)


def test_ocr_registry_paddle_fallback_when_unavailable():
    """Verify PaddleOCR falls back to Tesseract when Paddle runtime is missing."""
    registry = OcrEngineRegistry()
    # On this host, paddleocr is not installed, so paddle_engine.is_available() is False
    engine = registry.get_engine("paddleocr")
    assert isinstance(engine, TesseractOcrEngine)


def test_ocr_registry_custom_engine():
    """Verify custom engine registration and retrieval."""
    registry = OcrEngineRegistry()
    mock_engine = MagicMock(spec=OcrEngineProtocol)
    mock_engine.is_available.return_value = True

    registry.register_engine("mock_neural_ocr", mock_engine)
    retrieved = registry.get_engine("mock_neural_ocr")

    assert retrieved == mock_engine
