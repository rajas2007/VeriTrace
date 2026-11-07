"""Extraction capability package for digital vector text, raster OCR, normalizers, and tables."""

from veritrace.capabilities.extraction.docling_adapter import (
    DoclingDocumentResult,
    DoclingLayoutAdapter,
    DoclingLayoutElement,
)
from veritrace.capabilities.extraction.engine_registry import (
    OcrEngineRegistry,
    ocr_registry,
)
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
from veritrace.capabilities.extraction.paddle_ocr_engine import PaddleOcrEngine
from veritrace.capabilities.extraction.pdf_text_extractor import (
    DocumentDigitalExtraction,
    ExtractedBlockData,
    PageDigitalExtraction,
    PdfDigitalTextExtractor,
)
from veritrace.capabilities.extraction.table_extractor import (
    ExtractedTable,
    TableCell,
    TableExtractor,
)

__all__ = [
    "DoclingDocumentResult",
    "DoclingLayoutAdapter",
    "DoclingLayoutElement",
    "DocumentDigitalExtraction",
    "ExtractedBlockData",
    "ExtractedTable",
    "HybridDocumentExtractor",
    "OcrEngineProtocol",
    "OcrEngineRegistry",
    "OcrPageResult",
    "PaddleOcrEngine",
    "PageDigitalExtraction",
    "PdfDigitalTextExtractor",
    "TableCell",
    "TableExtractor",
    "TesseractOcrEngine",
    "TextExtractorProtocol",
    "TextNormalizer",
    "ocr_registry",
]
