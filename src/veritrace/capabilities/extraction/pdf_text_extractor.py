"""PDF digital vector text extraction using PyMuPDF.

Extracts text page-by-page preserving exact order, verbatim text content,
page dimensions, and bounding boxes. Identifies scanned pages with no
usable digital text without false positive claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pymupdf

from veritrace.domain.enums.document import ExtractionSourceType, TextLayerType
from veritrace.domain.exceptions.base import CorruptedDocumentError
from veritrace.domain.value_objects.geometry import (
    NormalizedBoundingBox,
    PageDimensions,
)


@dataclass(slots=True)
class ExtractedBlockData:
    """Individual extracted text block with verbatim text and normalized geometry.

    NOTE on confidence: confidence=1.0 represents digital vector font extraction fidelity
    (direct lossless character stream decoding from font dictionaries without OCR recognizer
    uncertainty). It does NOT denote 100% semantic accuracy or field validation correctness.
    """

    block_index: int
    field_name: str
    field_value: str
    raw_text: str
    confidence: float
    normalized_bbox: NormalizedBoundingBox | None
    extraction_source: ExtractionSourceType = ExtractionSourceType.DIGITAL_TEXT
    ocr_engine: str = "PyMuPDF"
    ocr_model_version: str = pymupdf.__version__


@dataclass(slots=True)
class PageDigitalExtraction:
    """Extraction results for a single page of a PDF document."""

    page_number: int
    dimensions: PageDimensions
    image_bytes: bytes
    has_digital_text: bool
    text_layer_type: TextLayerType
    extracted_text: str
    word_count: int
    blocks: list[ExtractedBlockData] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentDigitalExtraction:
    """Aggregated extraction results across all pages of a PDF document."""

    total_pages: int
    pages_with_digital_text: int
    extraction_method: str
    timestamp: datetime
    pages: list[PageDigitalExtraction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PdfDigitalTextExtractor:
    """Extracts digital text and page dimensions from PDF documents using PyMuPDF.

    Reading order notes:
    Block extraction preserves PyMuPDF physical stream order (top-to-bottom, left-to-right).
    In multi-column, table, or complex multi-pane layouts, natural reading order is not
    guaranteed and requires downstream semantic layout analysis.
    """

    def __init__(self, target_dpi: int = 300, raster_preview_dpi: int = 150) -> None:
        self._target_dpi = target_dpi
        self._preview_dpi = raster_preview_dpi

    def extract(self, content_or_path: bytes | str) -> DocumentDigitalExtraction:
        """Extract text and metadata page by page from PDF data or file path."""
        try:
            if isinstance(content_or_path, bytes):
                doc = pymupdf.open(stream=content_or_path, filetype="pdf")
            else:
                doc = pymupdf.open(content_or_path)
        except Exception as exc:
            raise CorruptedDocumentError(f"Failed to open PDF document: {exc}") from exc

        try:
            total_pages = len(doc)
            if total_pages == 0:
                raise CorruptedDocumentError("PDF document contains 0 pages")

            pages_results: list[PageDigitalExtraction] = []
            doc_warnings: list[str] = []
            pages_with_digital_text = 0

            for page_idx in range(total_pages):
                page_number = page_idx + 1
                page = doc[page_idx]
                rect = page.rect

                # Capture dimensions at target DPI (PDF standard is 72 points per inch)
                width_pixels = max(1, int(rect.width * self._target_dpi / 72))
                height_pixels = max(1, int(rect.height * self._target_dpi / 72))
                dimensions = PageDimensions(
                    width_pixels=width_pixels,
                    height_pixels=height_pixels,
                    dpi=self._target_dpi,
                )

                # Generate raster preview PNG
                pix = page.get_pixmap(dpi=self._preview_dpi)
                image_bytes = pix.tobytes("png")

                # Extract verbatim text
                raw_page_text = page.get_text("text")
                clean_text = raw_page_text.strip()
                has_digital_text = bool(clean_text)

                page_warnings: list[str] = []
                if has_digital_text:
                    pages_with_digital_text += 1
                    text_layer_type = TextLayerType.VECTOR_NATIVE
                else:
                    text_layer_type = TextLayerType.SCANNED_RASTER
                    warn = (
                        f"Page {page_number} contains no usable digital text "
                        f"(scanned or raster image-only)."
                    )
                    page_warnings.append(warn)
                    doc_warnings.append(warn)

                # Extract structured text blocks with normalized coordinates
                blocks_data: list[ExtractedBlockData] = []
                if has_digital_text:
                    raw_blocks = page.get_text("blocks")
                    for b in raw_blocks:
                        # blocks format: (x0, y0, x1, y1, text, block_no, block_type)
                        if len(b) >= 7 and b[6] == 0:  # block_type 0 = text
                            bx0, by0, bx1, by1, btext, bno = b[0], b[1], b[2], b[3], b[4], b[5]
                            if not btext.strip():
                                continue

                            # Normalize coordinates to [0.0, 1.0]
                            page_w = max(1.0, rect.width)
                            page_h = max(1.0, rect.height)

                            ymin = max(0.0, min(1.0, by0 / page_h))
                            xmin = max(0.0, min(1.0, bx0 / page_w))
                            ymax = max(0.0, min(1.0, by1 / page_h))
                            xmax = max(0.0, min(1.0, bx1 / page_w))

                            # Enforce coordinate ordering and guard against zero-size boxes
                            if ymin > ymax:
                                ymin, ymax = ymax, ymin
                            if xmin > xmax:
                                xmin, xmax = xmax, xmin

                            if ymax <= ymin:
                                ymax = min(1.0, ymin + 0.001)
                                if ymax <= ymin:
                                    ymin = max(0.0, ymax - 0.001)

                            if xmax <= xmin:
                                xmax = min(1.0, xmin + 0.001)
                                if xmax <= xmin:
                                    xmin = max(0.0, xmax - 0.001)

                            bbox = NormalizedBoundingBox(
                                ymin=ymin,
                                xmin=xmin,
                                ymax=ymax,
                                xmax=xmax,
                            )

                            block_data = ExtractedBlockData(
                                block_index=bno,
                                field_name=f"p{page_number}_blk{bno}",
                                field_value=btext.strip(),
                                raw_text=btext,  # Verbatim preservation
                                confidence=1.0,  # Digital vector text has 1.0 confidence
                                normalized_bbox=bbox,
                                extraction_source=ExtractionSourceType.DIGITAL_TEXT,
                                ocr_engine="PyMuPDF",
                                ocr_model_version=pymupdf.__version__,
                            )
                            blocks_data.append(block_data)

                word_count = len(clean_text.split()) if clean_text else 0

                page_res = PageDigitalExtraction(
                    page_number=page_number,
                    dimensions=dimensions,
                    image_bytes=image_bytes,
                    has_digital_text=has_digital_text,
                    text_layer_type=text_layer_type,
                    extracted_text=raw_page_text,
                    word_count=word_count,
                    blocks=blocks_data,
                    warnings=page_warnings,
                )
                pages_results.append(page_res)

            return DocumentDigitalExtraction(
                total_pages=total_pages,
                pages_with_digital_text=pages_with_digital_text,
                extraction_method="PyMuPDF_DIGITAL_TEXT",
                timestamp=datetime.now(UTC),
                pages=pages_results,
                warnings=doc_warnings,
            )
        finally:
            doc.close()
