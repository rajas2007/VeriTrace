"""Optical Character Recognition (OCR) engine wrapper and protocol.

Extracts word and line tokens from raster images with normalized bounding boxes,
token confidences, and script identification, with robust fallback handling when
native OCR binaries are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
from PIL import Image

from veritrace.capabilities.extraction.normalizer import TextNormalizer
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox, PageDimensions
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken

# Try importing pytesseract
try:
    import pytesseract

    _PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    _PYTESSERACT_AVAILABLE = False


@dataclass(slots=True)
class OcrPageResult:
    """Structured extraction result produced by an OCR engine for an image canvas."""

    page_number: int
    dimensions: PageDimensions
    full_text: str
    tokens: list[ExtractedToken] = field(default_factory=list)
    mean_confidence: float = 0.0
    ocr_engine: str = "Tesseract"
    ocr_model_version: str = "unknown"
    warnings: list[str] = field(default_factory=list)


class OcrEngineProtocol(Protocol):
    """Protocol defining the interface for pluggable OCR recognition backends."""

    def is_available(self) -> bool:
        """Return True if the underlying OCR engine binary is installed and executable."""
        ...

    def extract_page_ocr(
        self,
        image_or_path: np.ndarray | Path | bytes,
        page_number: int = 1,
        lang: str = "eng",
    ) -> OcrPageResult:
        """Extract structured text tokens and bounding boxes from a raster canvas."""
        ...


class TesseractOcrEngine:
    """Tesseract 5.x OCR engine adapter.

    Converts image arrays or file paths into normalized ExtractedToken objects
    with bounding boxes in [ymin, xmin, ymax, xmax] coordinate space.
    """

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        self._tesseract_cmd = tesseract_cmd
        if tesseract_cmd and _PYTESSERACT_AVAILABLE and pytesseract:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._version_cache: str | None = None

    def is_available(self) -> bool:
        """Check if Tesseract executable is installed and responding."""
        if not _PYTESSERACT_AVAILABLE or pytesseract is None:
            return False
        if self._version_cache is not None:
            return True
        try:
            ver = pytesseract.get_tesseract_version()
            self._version_cache = str(ver)
            return True
        except Exception:
            return False

    def get_version(self) -> str:
        """Return cached or detected Tesseract version string."""
        if self._version_cache:
            return self._version_cache
        if not self.is_available():
            return "unavailable"
        try:
            assert pytesseract is not None
            ver = str(pytesseract.get_tesseract_version())
            self._version_cache = ver
            return ver
        except Exception:
            return "unknown"

    def _load_image(self, image_or_path: np.ndarray | Path | bytes) -> tuple[np.ndarray, int, int]:
        """Convert input to OpenCV BGR numpy array and return (img, width, height)."""
        if isinstance(image_or_path, np.ndarray):
            img = image_or_path
            h, w = img.shape[:2]
            return img, w, h

        if isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise FileNotFoundError(f"OCR image not found: {image_or_path}")
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

    def preprocess_image(self, img_bgr: np.ndarray) -> np.ndarray:
        """Preprocess canvas to improve OCR character recognition rate."""
        # Convert to grayscale
        if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 3:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_bgr.copy()

        # Mild contrast enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def extract_page_ocr(
        self,
        image_or_path: np.ndarray | Path | bytes,
        page_number: int = 1,
        lang: str = "eng",
    ) -> OcrPageResult:
        """Execute OCR extraction on a page image canvas."""
        img_bgr, width, height = self._load_image(image_or_path)
        dimensions = PageDimensions(width_pixels=width, height_pixels=height, dpi=300)

        if not self.is_available():
            # Graceful diagnostic fallback when Tesseract is not installed on the host
            return OcrPageResult(
                page_number=page_number,
                dimensions=dimensions,
                full_text="",
                tokens=[],
                mean_confidence=0.0,
                ocr_engine="Tesseract",
                ocr_model_version="unavailable",
                warnings=[
                    "Tesseract OCR executable is not available on system PATH. "
                    "Scanned image text recognition was bypassed."
                ],
            )

        assert pytesseract is not None

        try:
            processed_img = self.preprocess_image(img_bgr)
            pil_img = Image.fromarray(processed_img)

            # Request detailed word-level bounding boxes and confidences
            # output format: dict with keys ['left', 'top', 'width', 'height', 'conf', 'text', ...]
            data: dict[str, list[Any]] = pytesseract.image_to_data(
                pil_img,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )

            tokens: list[ExtractedToken] = []
            extracted_words: list[str] = []
            confidences: list[float] = []

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                raw_word = str(data["text"][i]).strip()
                conf_val = float(data["conf"][i])

                # Tesseract returns -1 for block, paragraph, and line headers
                if conf_val < 0.0 or not raw_word:
                    continue

                left = int(data["left"][i])
                top = int(data["top"][i])
                w = int(data["width"][i])
                h = int(data["height"][i])

                if w <= 0 or h <= 0:
                    continue

                # Compute normalized coordinates clamped to [0.0, 1.0]
                norm_xmin = max(0.0, min(1.0, left / width))
                norm_ymin = max(0.0, min(1.0, top / height))
                norm_xmax = max(0.0, min(1.0, (left + w) / width))
                norm_ymax = max(0.0, min(1.0, (top + h) / height))

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

                # Normalized confidence in [0.0, 1.0]
                norm_conf = max(0.0, min(1.0, conf_val / 100.0))

                # Script detection and text normalization
                script = TextNormalizer.detect_script(raw_word)
                normalized_text = TextNormalizer.normalize_for_matching(raw_word)

                token = ExtractedToken(
                    token_id=generate_id("tok_"),
                    text=normalized_text,
                    raw_text=raw_word,
                    normalized_bbox=bbox,
                    confidence=norm_conf,
                    page_number=page_number,
                    source_type=ExtractionSourceType.OCR,
                    language=lang.split("+")[0],
                    script=script,
                )
                tokens.append(token)
                extracted_words.append(raw_word)
                confidences.append(norm_conf)

            full_text = " ".join(extracted_words)
            mean_conf = float(np.mean(confidences)) if confidences else 0.0

            return OcrPageResult(
                page_number=page_number,
                dimensions=dimensions,
                full_text=full_text,
                tokens=tokens,
                mean_confidence=mean_conf,
                ocr_engine="Tesseract",
                ocr_model_version=self.get_version(),
            )

        except Exception as exc:
            return OcrPageResult(
                page_number=page_number,
                dimensions=dimensions,
                full_text="",
                tokens=[],
                mean_confidence=0.0,
                ocr_engine="Tesseract",
                ocr_model_version=self.get_version(),
                warnings=[f"OCR processing failed on page {page_number}: {exc}"],
            )
