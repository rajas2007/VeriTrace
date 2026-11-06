"""Hybrid Document Text Extractor combining digital vector text and raster OCR.

Seamlessly transitions between lossless digital PDF font streams and raster OCR
based on page text layer characteristics, ensuring complete provenance tracking.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol, runtime_checkable

import pymupdf

from veritrace.capabilities.extraction.normalizer import TextNormalizer
from veritrace.capabilities.extraction.ocr_engine import (
    OcrEngineProtocol,
    TesseractOcrEngine,
)
from veritrace.capabilities.extraction.pdf_text_extractor import (
    PdfDigitalTextExtractor,
)
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import (
    NormalizedBoundingBox,
)
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.domain.value_objects.multilingual import LanguageDetectionProfile
from veritrace.domain.value_objects.provenance import (
    ExtractedToken,
    ExtractionProvenance,
)
from veritrace.infrastructure.pdf.rasterizer import (
    DocumentRasterizerProtocol,
    PyMuPdfPageRasterizer,
)


@runtime_checkable
class TextExtractorProtocol(Protocol):
    """Protocol for extracting structured word tokens from a document page."""

    def extract_tokens(
        self, pdf_path: Path, page_num: int, raster_path: Path, lang: str = "eng"
    ) -> list[ExtractedToken]:
        """Extract structured tokens from a specific page."""
        ...


class HybridDocumentExtractor:
    """Enterprise text extractor that adaptively selects digital vector or OCR extraction."""

    def __init__(
        self,
        digital_extractor: PdfDigitalTextExtractor | None = None,
        ocr_engine: OcrEngineProtocol | None = None,
        rasterizer: DocumentRasterizerProtocol | None = None,
        digital_char_threshold: int = 30,
    ) -> None:
        self._digital_extractor = digital_extractor or PdfDigitalTextExtractor()
        self._ocr_engine = ocr_engine or TesseractOcrEngine()
        self._rasterizer = rasterizer or PyMuPdfPageRasterizer()
        self._digital_char_threshold = digital_char_threshold

    def extract_tokens(
        self, pdf_path: Path, page_num: int, raster_path: Path, lang: str = "eng"
    ) -> list[ExtractedToken]:
        """Implement TextExtractorProtocol.

        Attempts native digital extraction first; falls back to OCR if digital text is sparse.
        """
        if not pdf_path.exists():
            raise ValidationError(f"Document file not found: {pdf_path}")

        # If it's a PDF, check for native digital text
        if pdf_path.suffix.lower() == ".pdf":
            try:
                doc = pymupdf.open(str(pdf_path))
                if 1 <= page_num <= len(doc):
                    page = doc[page_num - 1]
                    digital_text = page.get_text("text").strip()
                    if len(digital_text) >= self._digital_char_threshold:
                        # Extract digital tokens directly with PyMuPDF
                        tokens = self._extract_digital_tokens(page, page_num, pdf_path)
                        doc.close()
                        return tokens
                doc.close()
            except Exception:
                pass  # Fall through to OCR

        # Fall back to OCR over the rasterized page
        if not raster_path.exists():
            # If raster doesn't exist yet, render it
            if pdf_path.suffix.lower() == ".pdf" and isinstance(
                self._rasterizer, PyMuPdfPageRasterizer
            ):
                raster_bytes, _ = self._rasterizer.render_page_to_bytes(pdf_path, page_num)
                ocr_res = self._ocr_engine.extract_page_ocr(
                    raster_bytes, page_number=page_num, lang=lang
                )
                return ocr_res.tokens
            elif pdf_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
                ocr_res = self._ocr_engine.extract_page_ocr(
                    pdf_path, page_number=page_num, lang=lang
                )
                return ocr_res.tokens

        ocr_res = self._ocr_engine.extract_page_ocr(raster_path, page_number=page_num, lang=lang)
        return ocr_res.tokens

    def _extract_digital_tokens(
        self, page: pymupdf.Page, page_num: int, pdf_path: Path
    ) -> list[ExtractedToken]:
        """Extract word-level ExtractedTokens from native digital PDF page."""
        rect = page.rect
        page_width = rect.width
        page_height = rect.height
        if page_width <= 0 or page_height <= 0:
            return []

        tokens: list[ExtractedToken] = []
        # get_text("words") returns tuples: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        words = page.get_text("words")
        for w in words:
            x0, y0, x1, y1, raw_word = w[:5]
            raw_text = str(raw_word).strip()
            if not raw_text:
                continue

            norm_xmin = max(0.0, min(1.0, x0 / page_width))
            norm_ymin = max(0.0, min(1.0, y0 / page_height))
            norm_xmax = max(0.0, min(1.0, x1 / page_width))
            norm_ymax = max(0.0, min(1.0, y1 / page_height))

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

            script = TextNormalizer.detect_script(raw_text)
            norm_text = TextNormalizer.normalize_for_matching(raw_text)

            token = ExtractedToken(
                token_id=generate_id("tok_"),
                text=norm_text,
                raw_text=raw_text,
                normalized_bbox=bbox,
                confidence=1.0,  # Lossless digital vector text decoding
                page_number=page_num,
                source_type=ExtractionSourceType.DIGITAL_TEXT,
                language="eng",
                script=script,
            )
            tokens.append(token)

        return tokens

    def extract_page_provenance(
        self,
        document_id: str,
        page_number: int,
        source_path: Path,
        raster_path: Path,
        lang: str = "eng",
    ) -> tuple[
        list[ExtractedToken],
        ExtractionProvenance,
        LanguageDetectionProfile,
        str,
        ExtractionSourceType,
    ]:
        """Extract tokens and complete audit provenance for a page."""
        start_time = time.perf_counter()
        tokens = self.extract_tokens(source_path, page_number, raster_path, lang=lang)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        full_raw_text = " ".join(t.raw_text for t in tokens)
        lang_profile = TextNormalizer.detect_language_profile(full_raw_text)

        has_digital = any(t.source_type == ExtractionSourceType.DIGITAL_TEXT for t in tokens)
        has_ocr = any(t.source_type == ExtractionSourceType.OCR for t in tokens)

        if has_digital and has_ocr:
            source_type = ExtractionSourceType.MIXED
        elif has_digital:
            source_type = ExtractionSourceType.DIGITAL_TEXT
        elif has_ocr:
            source_type = ExtractionSourceType.OCR
        else:
            source_type = ExtractionSourceType.NONE

        mean_conf = float(sum(t.confidence for t in tokens) / len(tokens)) if tokens else 1.0

        provenance = ExtractionProvenance(
            document_id=document_id,
            page_number=page_number,
            extractor_name="HybridDocumentExtractor",
            extractor_version="1.0.0",
            execution_time_ms=elapsed_ms,
            source_type=source_type,
            extraction_confidence=mean_conf,
            ocr_engine="Tesseract" if has_ocr else "PyMuPDF",
            language_profile=lang_profile,
        )

        return tokens, provenance, lang_profile, full_raw_text, source_type
