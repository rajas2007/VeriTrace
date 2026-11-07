"""Deterministic document classification based on structural content, keywords, and metadata."""

from __future__ import annotations

import re
from typing import Any

from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.document import DocumentType

# Weighted keyword definitions for industrial and commercial document types
_CLASSIFICATION_RULES: dict[DocumentType, list[tuple[str, float]]] = {
    DocumentType.PURCHASE_ORDER: [
        ("PURCHASE ORDER", 3.0),
        ("PURCHASE ORDER NO", 3.5),
        ("PO NO", 2.5),
        ("PO NUMBER", 2.5),
        ("PO-", 2.0),
        ("VENDOR", 1.0),
        ("BUYER", 1.0),
        ("SHIP TO", 1.0),
        ("BILL TO", 0.5),
        ("ORDER DATE", 1.5),
        ("PURCHASING AGENT", 2.0),
    ],
    DocumentType.DELIVERY_CHALLAN: [
        ("DELIVERY CHALLAN", 3.5),
        ("CHALLAN NO", 3.0),
        ("CHALLAN NUMBER", 3.0),
        ("DC NO", 2.5),
        ("DC-", 2.0),
        ("DESPATCH", 1.5),
        ("DISPATCH", 1.5),
        ("CONSIGNEE", 1.5),
        ("VEHICLE NO", 2.0),
        ("TRANSPORTER", 1.5),
        ("DELIVERY NOTE", 2.5),
        ("RECEIVED BY", 1.0),
    ],
    DocumentType.MILL_TEST_CERT: [
        ("MILL TEST CERTIFICATE", 4.0),
        ("MATERIAL TEST CERTIFICATE", 4.0),
        ("INSPECTION CERTIFICATE", 3.0),
        ("TEST CERTIFICATE", 2.5),
        ("MTC", 2.0),
        ("HEAT NO", 3.0),
        ("HEAT NUMBER", 3.0),
        ("CHEMICAL COMPOSITION", 2.5),
        ("MECHANICAL PROPERTIES", 2.5),
        ("TENSILE STRENGTH", 2.0),
        ("YIELD STRENGTH", 2.0),
        ("METALLURGICAL", 2.0),
        ("EN 10204", 3.0),
        ("ASTM", 1.5),
    ],
    DocumentType.COMMERCIAL_INVOICE: [
        ("TAX INVOICE", 3.5),
        ("COMMERCIAL INVOICE", 3.5),
        ("INVOICE NO", 3.0),
        ("INVOICE NUMBER", 3.0),
        ("INV NO", 2.5),
        ("INV-", 2.0),
        ("GSTIN", 2.0),
        ("TAXABLE VALUE", 2.0),
        ("CGST", 2.0),
        ("SGST", 2.0),
        ("IGST", 2.0),
        ("TOTAL AMOUNT", 1.0),
        ("BILL TO", 1.0),
    ],
    DocumentType.BANK_STATEMENT: [
        ("BANK STATEMENT", 4.0),
        ("ACCOUNT STATEMENT", 3.5),
        ("ACCOUNT NUMBER", 2.5),
        ("A/C NO", 2.0),
        ("IFSC", 2.5),
        ("OPENING BALANCE", 2.0),
        ("CLOSING BALANCE", 2.0),
        ("WITHDRAWAL", 1.5),
        ("DEPOSIT", 1.5),
    ],
    DocumentType.SALARY_SLIP: [
        ("SALARY SLIP", 4.0),
        ("PAY SLIP", 4.0),
        ("PAYSLIP", 4.0),
        ("BASIC PAY", 2.5),
        ("BASIC SALARY", 2.5),
        ("HRA", 2.0),
        ("PROVIDENT FUND", 2.0),
        ("NET SALARY", 2.5),
        ("NET PAY", 2.5),
    ],
    DocumentType.FINANCIAL_STATEMENT: [
        ("BALANCE SHEET", 4.0),
        ("PROFIT AND LOSS", 4.0),
        ("PROFIT & LOSS", 4.0),
        ("ANNUAL REPORT", 3.0),
        ("AUDITED FINANCIAL", 3.0),
        ("STATEMENT OF PROFIT AND LOSS", 4.0),
    ],
}

# Filename prefix / pattern indicators
_FILENAME_HINTS: list[tuple[str, DocumentType, float]] = [
    (r"^PO[-_]", DocumentType.PURCHASE_ORDER, 2.5),
    (r"PURCHASE.*ORDER", DocumentType.PURCHASE_ORDER, 3.0),
    (r"^DC[-_]", DocumentType.DELIVERY_CHALLAN, 2.5),
    (r"CHALLAN", DocumentType.DELIVERY_CHALLAN, 3.0),
    (r"^MTC[-_]", DocumentType.MILL_TEST_CERT, 2.5),
    (r"MILL.*TEST", DocumentType.MILL_TEST_CERT, 3.0),
    (r"CERTIFICATE", DocumentType.MILL_TEST_CERT, 1.5),
    (r"^INV[-_]", DocumentType.COMMERCIAL_INVOICE, 2.5),
    (r"INVOICE", DocumentType.COMMERCIAL_INVOICE, 3.0),
    (r"BANK.*STATEMENT", DocumentType.BANK_STATEMENT, 3.0),
    (r"PAYSLIP|SALARY", DocumentType.SALARY_SLIP, 3.0),
]


class DocumentClassifier:
    """Deterministic, rule-based document classifier evaluating structural keywords and metadata."""

    def __init__(self, confidence_threshold: float = 0.25) -> None:
        self._confidence_threshold = confidence_threshold

    def classify(
        self,
        text: str | None = None,
        filename: str | None = None,
        extracted_fields: list[ExtractedField] | list[Any] | None = None,
    ) -> tuple[DocumentType, float]:
        """Classify a document into a known DocumentType with associated confidence score.

        Args:
            text: Extracted raw text or concatenated OCR tokens.
            filename: Original document filename.
            extracted_fields: Optional list of ExtractedField entities.

        Returns:
            Tuple of (DocumentType, confidence in [0.0, 1.0]).
        """
        combined_text_parts: list[str] = []
        if text:
            combined_text_parts.append(text.upper())
        if filename:
            combined_text_parts.append(filename.upper())
        if extracted_fields:
            for field in extracted_fields:
                if isinstance(field, ExtractedField):
                    combined_text_parts.append(field.field_name.upper())
                    combined_text_parts.append(field.field_value.upper())

        combined_text = " \n ".join(combined_text_parts)
        if not combined_text.strip():
            return DocumentType.UNCLASSIFIED, 0.0

        keyword_scores: dict[DocumentType, float] = {dtype: 0.0 for dtype in _CLASSIFICATION_RULES}

        # 1. Evaluate keyword matches against extracted content
        for dtype, rules in _CLASSIFICATION_RULES.items():
            for kw, weight in rules:
                if kw in combined_text:
                    keyword_scores[dtype] += weight

        # 2. Evaluate filename pattern hints as supplementary signals
        # Strict Precondition: Filename hints must NOT independently produce a confident
        # document classification if the document body contains zero corresponding keywords.
        scores: dict[DocumentType, float] = dict(keyword_scores)
        if filename:
            fn_upper = filename.upper()
            for pattern, dtype, weight in _FILENAME_HINTS:
                # Supplementary boost only if extracted keywords are present
                if re.search(pattern, fn_upper) and keyword_scores[dtype] > 0.0:
                    scores[dtype] += weight

        # 3. Find top scoring document type
        best_type = DocumentType.UNCLASSIFIED
        best_score = 0.0
        for dtype, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = dtype

        if best_score <= 0.0:
            return DocumentType.UNCLASSIFIED, 0.0

        # Normalize confidence to [0.0, 1.0] with saturation above score of 6.0
        confidence = min(round(best_score / 6.0, 3), 1.0)
        if confidence < self._confidence_threshold:
            return DocumentType.UNCLASSIFIED, confidence

        return best_type, confidence
