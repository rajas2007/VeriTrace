"""Unit tests for PdfDigitalTextExtractor capability."""

from __future__ import annotations

import io

import pymupdf
import pytest
from PIL import Image

from veritrace.capabilities.extraction.pdf_text_extractor import (
    PdfDigitalTextExtractor,
)
from veritrace.domain.enums.document import ExtractionSourceType, TextLayerType
from veritrace.domain.exceptions.base import CorruptedDocumentError


def _create_digital_pdf(pages_text: list[str]) -> bytes:
    """Helper creating in-memory multi-page digital PDF with given text per page."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)
        if text:
            page.insert_text((50, 100), text, fontsize=12)
    buf = doc.tobytes()
    doc.close()
    return bytes(buf)


def _create_scanned_image_pdf() -> bytes:
    """Helper creating a PDF containing an image but zero digital vector text."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Insert a small raster image
    img = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    page.insert_image(pymupdf.Rect(50, 50, 150, 150), stream=img_byte_arr.getvalue())

    buf = doc.tobytes()
    doc.close()
    return bytes(buf)


def test_extract_multi_page_pdf_with_digital_text() -> None:
    """Verify digital text extraction across multiple ordered pages."""
    extractor = PdfDigitalTextExtractor(target_dpi=300)
    pdf_bytes = _create_digital_pdf(
        [
            "Page 1: Commercial Tax Invoice Header",
            "Page 2: Line Item Details and Total Amounts",
        ]
    )

    res = extractor.extract(pdf_bytes)

    assert res.total_pages == 2
    assert res.pages_with_digital_text == 2
    assert res.extraction_method == "PyMuPDF_DIGITAL_TEXT"
    assert len(res.pages) == 2

    p1 = res.pages[0]
    assert p1.page_number == 1
    assert p1.has_digital_text is True
    assert p1.text_layer_type == TextLayerType.VECTOR_NATIVE
    assert "Commercial Tax Invoice Header" in p1.extracted_text
    assert p1.word_count > 0
    assert len(p1.blocks) >= 1
    assert p1.blocks[0].confidence == 1.0
    assert p1.blocks[0].extraction_source == ExtractionSourceType.DIGITAL_TEXT

    p2 = res.pages[1]
    assert p2.page_number == 2
    assert p2.has_digital_text is True
    assert "Line Item Details" in p2.extracted_text


def test_extract_scanned_pdf_flags_no_digital_text() -> None:
    """Verify that scanned/image-only PDFs are flagged with has_digital_text=False and warning."""
    extractor = PdfDigitalTextExtractor(target_dpi=300)
    scanned_pdf = _create_scanned_image_pdf()

    res = extractor.extract(scanned_pdf)

    assert res.total_pages == 1
    assert res.pages_with_digital_text == 0
    page = res.pages[0]
    assert page.has_digital_text is False
    assert page.text_layer_type == TextLayerType.SCANNED_RASTER
    assert page.word_count == 0
    assert len(page.blocks) == 0
    assert len(page.warnings) >= 1
    assert "contains no usable digital text" in page.warnings[0]


def test_extract_empty_page_generates_warnings() -> None:
    """Verify blank page yields no digital text and records warning."""
    extractor = PdfDigitalTextExtractor(target_dpi=300)
    blank_pdf = _create_digital_pdf([""])

    res = extractor.extract(blank_pdf)
    assert res.total_pages == 1
    assert res.pages_with_digital_text == 0
    assert len(res.warnings) >= 1


def test_extract_preserves_page_ordering_and_dimensions() -> None:
    """Verify page dimensions and pixel scaling at 300 DPI."""
    extractor = PdfDigitalTextExtractor(target_dpi=300)
    # A4 dimensions: 595 x 842 points. At 300 DPI: ~2479 x 3508 pixels.
    pdf_bytes = _create_digital_pdf(["Dimension verification page"])

    res = extractor.extract(pdf_bytes)
    page = res.pages[0]
    assert page.dimensions.dpi == 300
    assert 2470 <= page.dimensions.width_pixels <= 2490
    assert 3500 <= page.dimensions.height_pixels <= 3520
    assert len(page.image_bytes) > 0  # Preview raster rendered


def test_extract_corrupted_pdf_raises() -> None:
    """Verify invalid PDF stream raises CorruptedDocumentError."""
    extractor = PdfDigitalTextExtractor()
    with pytest.raises(CorruptedDocumentError, match="Failed to open PDF document"):
        extractor.extract(b"Not a real PDF file contents")


def test_extract_verbatim_text_preservation() -> None:
    """Verify verbatim extraction does not alter or normalize special characters or numbers."""
    extractor = PdfDigitalTextExtractor()
    special_text = "Tax ID: #987-AB/2026 -- Total: Rs. 1,45,000.50 [CONFIDENTIAL]"
    pdf_bytes = _create_digital_pdf([special_text])

    res = extractor.extract(pdf_bytes)
    assert special_text in res.pages[0].extracted_text
