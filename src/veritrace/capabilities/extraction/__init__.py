"""Extraction capability package for digital vector text, raster OCR, and normalizers."""

from veritrace.capabilities.extraction.hybrid_extractor import (
    HybridDocumentExtractor,
    TextExtractorProtocol,
)
from veritrace.capabilities.extraction.normalizer import TextNormalizer
from veritrace.capabilities.extraction.ocr_engine import (
    OcrEngineProtocol,
    OcrPageResult,
    TesseractOcrEngine,
)
from veritrace.capabilities.extraction.pdf_text_extractor import (
    DocumentDigitalExtraction,
    ExtractedBlockData,
    PageDigitalExtraction,
    PdfDigitalTextExtractor,
)

__all__ = [
    "DocumentDigitalExtraction",
    "ExtractedBlockData",
    "HybridDocumentExtractor",
    "OcrEngineProtocol",
    "OcrPageResult",
    "PageDigitalExtraction",
    "PdfDigitalTextExtractor",
    "TesseractOcrEngine",
    "TextExtractorProtocol",
    "TextNormalizer",
]
