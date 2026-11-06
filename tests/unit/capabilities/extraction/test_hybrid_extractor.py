"""Unit tests for HybridDocumentExtractor combining digital text and raster OCR."""

from pathlib import Path
from unittest.mock import MagicMock

import pymupdf
import pytest

from veritrace.capabilities.extraction.hybrid_extractor import (
    HybridDocumentExtractor,
    TextExtractorProtocol,
)
from veritrace.capabilities.extraction.ocr_engine import OcrPageResult
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox, PageDimensions
from veritrace.domain.value_objects.provenance import ExtractedToken


@pytest.fixture
def digital_pdf(tmp_path: Path) -> Path:
    """Create a digital PDF with rich selectable vector text."""
    p = tmp_path / "digital.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text(
        pymupdf.Point(72, 100),
        "Purchase Order PO-2026-9901 Total Amount: INR 1,85,000 Verified",
        fontsize=14,
    )
    doc.save(str(p))
    doc.close()
    return p


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with no digital text (simulating scanned raster image)."""
    p = tmp_path / "scanned.pdf"
    doc = pymupdf.open()
    doc.new_page(width=600, height=800)
    doc.save(str(p))
    doc.close()
    return p


def test_protocol_conformance():
    """Verify HybridDocumentExtractor conforms to TextExtractorProtocol."""
    extractor = HybridDocumentExtractor()
    assert isinstance(extractor, TextExtractorProtocol)


def test_extract_tokens_digital_path(digital_pdf: Path, tmp_path: Path):
    """Verify digital PDF uses fast PyMuPDF extraction with confidence 1.0."""
    extractor = HybridDocumentExtractor()
    raster_path = tmp_path / "unused_raster.png"

    tokens = extractor.extract_tokens(digital_pdf, page_num=1, raster_path=raster_path)

    assert len(tokens) >= 5
    for t in tokens:
        assert t.source_type == ExtractionSourceType.DIGITAL_TEXT
        assert t.confidence == 1.0
        assert 0.0 <= t.normalized_bbox.ymin <= 1.0


def test_extract_tokens_ocr_fallback(empty_pdf: Path, tmp_path: Path):
    """Verify empty digital text falls back to OCR engine."""
    mock_ocr = MagicMock()
    mock_token = ExtractedToken(
        token_id="tok_mock1",
        text="SCANNED_WORD",
        raw_text="SCANNED_WORD",
        normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.2, xmax=0.3),
        confidence=0.88,
        page_number=1,
        source_type=ExtractionSourceType.OCR,
        language="eng",
        script="Latn",
    )
    mock_ocr.extract_page_ocr.return_value = OcrPageResult(
        page_number=1,
        dimensions=PageDimensions(width_pixels=600, height_pixels=800, dpi=300),
        full_text="SCANNED_WORD",
        tokens=[mock_token],
        mean_confidence=0.88,
    )

    extractor = HybridDocumentExtractor(ocr_engine=mock_ocr)
    raster_path = tmp_path / "page_0001.png"

    tokens = extractor.extract_tokens(empty_pdf, page_num=1, raster_path=raster_path)

    assert len(tokens) == 1
    assert tokens[0].source_type == ExtractionSourceType.OCR
    assert tokens[0].text == "SCANNED_WORD"
    assert mock_ocr.extract_page_ocr.called


def test_extract_page_provenance(digital_pdf: Path, tmp_path: Path):
    """Verify extract_page_provenance generates complete audit record and language profile."""
    extractor = HybridDocumentExtractor()
    raster_path = tmp_path / "page_0001.png"

    tokens, prov, lang_prof, full_text, source_type = extractor.extract_page_provenance(
        document_id="doc_test123",
        page_number=1,
        source_path=digital_pdf,
        raster_path=raster_path,
    )

    assert len(tokens) > 0
    assert prov.document_id == "doc_test123"
    assert prov.page_number == 1
    assert prov.execution_time_ms >= 0.0
    assert prov.source_type == ExtractionSourceType.DIGITAL_TEXT
    assert lang_prof.primary_language == "eng"
    assert "Purchase Order" in full_text
