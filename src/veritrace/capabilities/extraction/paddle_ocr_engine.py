"""PaddleOCR engine adapter for multilingual text extraction.

Implements OcrEngineProtocol for high-accuracy Devanagari (Hindi, Marathi)
and regional Indian script extraction with token-level bounding boxes, confidences,
and graceful fallback handling when PaddleOCR binaries are unavailable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from veritrace.capabilities.extraction.normalizer import TextNormalizer
from veritrace.capabilities.extraction.ocr_engine import OcrPageResult
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox, PageDimensions
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken

logger = logging.getLogger("veritrace.capabilities.extraction.paddle_ocr")

# Safe import check for paddleocr without hard runtime failure
try:
    import paddleocr  # type: ignore[import-not-found,import-untyped]

    _PADDLE_AVAILABLE = True
except (ImportError, Exception):
    paddleocr = None
    _PADDLE_AVAILABLE = False

PADDLE_AVAILABLE: bool = _PADDLE_AVAILABLE


# Language mapping: VeriTrace ISO 639-3 / BCP-47 -> PaddleOCR language codes
_LANGUAGE_MAP: dict[str, str] = {
    "eng": "en",
    "en": "en",
    "hin": "hi",
    "hi": "hi",
    "mar": "hi",  # PaddleOCR uses Devanagari recognizer for Marathi
    "mr": "hi",
    "tam": "ta",
    "ta": "ta",
    "tel": "te",
    "te": "te",
    "ben": "beng",
    "bn": "beng",
    "guj": "guj",
    "gu": "guj",
    "kan": "knda",
    "kn": "knda",
    "mal": "mal",
    "ml": "mal",
    "urd": "ur",
    "ur": "ur",
}


class PaddleOcrEngine:
    """PaddleOCR adapter implementing OcrEngineProtocol.

    Converts image arrays or file paths into normalized ExtractedToken objects
    with bounding boxes in [ymin, xmin, ymax, xmax] coordinate space.
    """

    def __init__(
        self,
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        ocr_runner: Callable[..., Any] | None = None,
        model_version: str = "v4",
    ) -> None:
        self._use_angle_cls = use_angle_cls
        self._use_gpu = use_gpu
        self._custom_runner = ocr_runner
        self._model_version = model_version
        self._ocr_instances: dict[str, Any] = {}

    def is_available(self) -> bool:
        """Return True if PaddleOCR is installed or a custom runner is provided."""
        if self._custom_runner is not None:
            return True
        return _PADDLE_AVAILABLE and paddleocr is not None

    def get_version(self) -> str:
        """Return cached or detected PaddleOCR version string."""
        if not self.is_available():
            return "unavailable"
        if hasattr(paddleocr, "__version__"):
            return str(paddleocr.__version__)
        return self._model_version

    def map_language_code(self, lang: str) -> str:
        """Map VeriTrace language code to PaddleOCR language code."""
        return self._get_paddle_lang(lang)

    def _get_paddle_lang(self, lang: str) -> str:
        """Map VeriTrace language code to PaddleOCR language code."""
        primary_lang = lang.split("+")[0].strip().lower()
        return _LANGUAGE_MAP.get(primary_lang, "en")

    def _get_ocr_instance(self, paddle_lang: str) -> Any:
        """Lazy-initialize and cache PaddleOCR instance per language."""
        if self._custom_runner is not None:
            return None

        if paddle_lang not in self._ocr_instances:
            if not _PADDLE_AVAILABLE or paddleocr is None:
                raise RuntimeError("PaddleOCR runtime is not installed on this host.")

            logger.info(
                "Initializing PaddleOCR instance (lang='%s', use_gpu=%s, model='%s')",
                paddle_lang,
                self._use_gpu,
                self._model_version,
            )
            self._ocr_instances[paddle_lang] = paddleocr.PaddleOCR(
                use_angle_cls=self._use_angle_cls,
                lang=paddle_lang,
                use_gpu=self._use_gpu,
                show_log=False,
            )
        return self._ocr_instances[paddle_lang]

    def _load_image(self, image_or_path: np.ndarray | Path | bytes) -> tuple[np.ndarray, int, int]:
        """Convert input to OpenCV BGR numpy array and return (img, width, height)."""
        if isinstance(image_or_path, np.ndarray):
            img = image_or_path
            h, w = img.shape[:2]
            return img, w, h

        if isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise FileNotFoundError(f"Image not found: {image_or_path}")
            decoded_path = cv2.imread(str(image_or_path))
            if decoded_path is None:
                raise ValueError(f"Failed to decode image from path: {image_or_path}")
            h, w = decoded_path.shape[:2]
            return decoded_path, w, h

        if isinstance(image_or_path, bytes):
            nparr = np.frombuffer(image_or_path, np.uint8)
            decoded_bytes = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if decoded_bytes is None:
                raise ValueError("Failed to decode image from bytes")
            h, w = decoded_bytes.shape[:2]
            return decoded_bytes, w, h

        raise TypeError(f"Unsupported image type: {type(image_or_path)}")

    def extract_page_ocr(
        self,
        image_or_path: np.ndarray | Path | bytes,
        page_number: int = 1,
        lang: str = "eng",
    ) -> OcrPageResult:
        """Execute PaddleOCR extraction on an image canvas.

        Extracts line/token segments, converts 4-point polygon bounding boxes to
        normalized [ymin, xmin, ymax, xmax] coordinates, and performs Unicode normalization.
        """
        img_bgr, width, height = self._load_image(image_or_path)
        dimensions = PageDimensions(width_pixels=width, height_pixels=height, dpi=300)

        if not self.is_available():
            return OcrPageResult(
                page_number=page_number,
                dimensions=dimensions,
                full_text="",
                tokens=[],
                mean_confidence=0.0,
                ocr_engine="PaddleOCR",
                ocr_model_version="unavailable",
                warnings=[
                    "PaddleOCR runtime is not installed or available on this system. "
                    "Multilingual extraction bypassed; fall back to Tesseract."
                ],
            )

        paddle_lang = self._get_paddle_lang(lang)

        try:
            # Execute OCR using custom runner or native PaddleOCR
            if self._custom_runner is not None:
                raw_results = self._custom_runner(img_bgr, paddle_lang)
            else:
                ocr_engine = self._get_ocr_instance(paddle_lang)
                raw_results = ocr_engine.ocr(img_bgr, cls=self._use_angle_cls)

            tokens: list[ExtractedToken] = []
            extracted_words: list[str] = []
            confidences: list[float] = []

            # PaddleOCR returns a list of pages: [[ [box, (text, conf)], ... ]]
            lines = (
                raw_results[0]
                if (
                    raw_results
                    and isinstance(raw_results, list)
                    and len(raw_results) > 0
                    and raw_results[0] is not None
                )
                else []
            )

            for item in lines:
                if not item or len(item) < 2:
                    continue

                box_points = item[0]  # 4 corners: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = item[1]  # (text, confidence)
                if not isinstance(text_info, (tuple, list)) or len(text_info) < 2:
                    continue

                raw_text = str(text_info[0]).strip()
                conf_val = float(text_info[1])

                if not raw_text or conf_val <= 0.0:
                    continue

                # Extract bounding coordinates from 4 polygon vertices
                xs = [float(p[0]) for p in box_points]
                ys = [float(p[1]) for p in box_points]

                min_x = min(xs)
                max_x = max(xs)
                min_y = min(ys)
                max_y = max(ys)

                # Normalize coordinates clamped to [0.0, 1.0]
                norm_xmin = max(0.0, min(1.0, min_x / width))
                norm_ymin = max(0.0, min(1.0, min_y / height))
                norm_xmax = max(0.0, min(1.0, max_x / width))
                norm_ymax = max(0.0, min(1.0, max_y / height))

                # Guard against degenerate bounding boxes
                if norm_xmin >= norm_xmax:
                    norm_xmax = min(1.0, norm_xmin + 0.001)
                if norm_ymin >= norm_ymax:
                    norm_ymax = min(1.0, norm_ymin + 0.001)

                bbox = NormalizedBoundingBox(
                    ymin=norm_ymin,
                    xmin=norm_xmin,
                    ymax=norm_ymax,
                    xmax=norm_xmax,
                )

                # Normalized confidence [0.0, 1.0]
                norm_conf = max(0.0, min(1.0, conf_val))

                # Script detection and Unicode text normalization
                script = TextNormalizer.detect_script(raw_text)
                normalized_text = TextNormalizer.normalize_for_matching(raw_text)

                token = ExtractedToken(
                    token_id=generate_id("tok_"),
                    text=normalized_text,
                    raw_text=raw_text,
                    normalized_bbox=bbox,
                    confidence=norm_conf,
                    page_number=page_number,
                    source_type=ExtractionSourceType.OCR,
                    language=lang.split("+")[0],
                    script=script,
                )
                tokens.append(token)
                extracted_words.append(raw_text)
                confidences.append(norm_conf)

            full_text = " ".join(extracted_words)
            mean_conf = float(np.mean(confidences)) if confidences else 0.0

            return OcrPageResult(
                page_number=page_number,
                dimensions=dimensions,
                full_text=full_text,
                tokens=tokens,
                mean_confidence=mean_conf,
                ocr_engine="PaddleOCR",
                ocr_model_version=self.get_version(),
            )

        except Exception as exc:
            logger.error("PaddleOCR execution failed on page %d: %s", page_number, exc)
            return OcrPageResult(
                page_number=page_number,
                dimensions=dimensions,
                full_text="",
                tokens=[],
                mean_confidence=0.0,
                ocr_engine="PaddleOCR",
                ocr_model_version=self.get_version(),
                warnings=[f"PaddleOCR execution error on page {page_number}: {exc}"],
            )
