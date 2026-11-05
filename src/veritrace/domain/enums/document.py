"""Document-related domain enums."""

from enum import StrEnum


class DocumentType(StrEnum):
    """Categorization of industrial documents submitted for analysis."""

    UNCLASSIFIED = "UNCLASSIFIED"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    DELIVERY_CHALLAN = "DELIVERY_CHALLAN"
    MILL_TEST_CERT = "MILL_TEST_CERT"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    IDENTITY_PROOF = "IDENTITY_PROOF"
    INCOME_PROOF = "INCOME_PROOF"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    COMMERCIAL_RECORD = "COMMERCIAL_RECORD"
    GENERAL_AFFIDAVIT = "GENERAL_AFFIDAVIT"
    SALARY_SLIP = "SALARY_SLIP"
    BANK_STATEMENT = "BANK_STATEMENT"


class DocumentStatus(StrEnum):
    """Ingestion and processing state of an individual file."""

    UPLOADED = "UPLOADED"
    PROCESSED = "PROCESSED"
    ERROR_CORRUPTED = "ERROR_CORRUPTED"


class QualityStatus(StrEnum):
    """Quality verification gate classification for an extracted document."""

    UNVERIFIED = "UNVERIFIED"
    VERIFIED_HIGH = "VERIFIED_HIGH"
    DEGRADED_SCAN = "DEGRADED_SCAN"


class ExtractionSourceType(StrEnum):
    """Origin mechanism of extracted text."""

    DIGITAL_TEXT = "digital_text"  # Native PDF vector font glyphs
    OCR = "ocr"  # Raster optical character recognition
    MIXED = "mixed"  # Page contains both digital vector and OCR text
    NONE = "none"  # Blank page or unextractable visual content


class TextLayerType(StrEnum):
    """Text layer representation on a rendered document page."""

    VECTOR_NATIVE = "VECTOR_NATIVE"
    SCANNED_RASTER = "SCANNED_RASTER"
    HYBRID = "HYBRID"
