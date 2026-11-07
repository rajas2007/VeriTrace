"""OCR Engine Registry and Routing Service.

Provides centralized management and fallback routing across OCR recognition backends
(Tesseract, PaddleOCR, and custom engines) conforming to OcrEngineProtocol.
"""

from __future__ import annotations

import logging

from veritrace.capabilities.extraction.ocr_engine import (
    OcrEngineProtocol,
    TesseractOcrEngine,
)
from veritrace.capabilities.extraction.paddle_ocr_engine import (
    PaddleOcrEngine,
)

logger = logging.getLogger("veritrace.capabilities.extraction.engine_registry")


class OcrEngineRegistry:
    """Registry managing pluggable OCR engines with automatic fallback routing."""

    def __init__(self) -> None:
        self._custom_engines: dict[str, OcrEngineProtocol] = {}

    def register_engine(self, name: str, engine: OcrEngineProtocol) -> None:
        """Register a custom or specialized OCR engine."""
        self._custom_engines[name.lower()] = engine

    def get_engine(self, engine_name: str | None = None) -> OcrEngineProtocol:
        """Resolve requested OCR engine with graceful fallback.

        Args:
            engine_name: 'tesseract', 'paddleocr', or a registered custom engine name.
                         If None, defaults to 'tesseract'.

        Returns:
            An operational OcrEngineProtocol implementation.
        """
        requested = (engine_name or "tesseract").lower().strip()

        # 1. Check custom registry
        if requested in self._custom_engines:
            engine = self._custom_engines[requested]
            if engine.is_available():
                return engine
            logger.warning(
                "Custom OCR engine '%s' is not available; falling back to Tesseract.",
                requested,
            )

        # 2. Check PaddleOCR
        if requested in ("paddle", "paddleocr"):
            paddle_engine = PaddleOcrEngine()
            if paddle_engine.is_available():
                logger.info("Routing OCR extraction to PaddleOCR multilingual engine.")
                return paddle_engine
            logger.warning(
                "PaddleOCR requested but runtime/models are not installed. "
                "Falling back to default Tesseract engine."
            )

        # 3. Default to Tesseract
        return TesseractOcrEngine()


# Global shared instance
ocr_registry = OcrEngineRegistry()
