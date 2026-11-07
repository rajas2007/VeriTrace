"""Unit tests for deterministic document classifier."""

from veritrace.capabilities.classification.classifier import DocumentClassifier
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.document import DocumentType, ExtractionSourceType


def test_classify_purchase_order_from_text():
    classifier = DocumentClassifier()
    text = (
        "Apex Heavy Engineering Ltd\nPURCHASE ORDER\nPO Number: PO-2026-IND-001\nVendor: Steel Corp"
    )
    dtype, conf = classifier.classify(text=text)
    assert dtype == DocumentType.PURCHASE_ORDER
    assert conf > 0.5


def test_classify_delivery_challan_from_filename_and_text():
    classifier = DocumentClassifier()
    text = (
        "DELIVERY CHALLAN\n"
        "Challan No: DC-98741\n"
        "Consignee: Apex Heavy Engineering\n"
        "Vehicle No: MH-12-Q-4421"
    )
    dtype, conf = classifier.classify(text=text, filename="DC-98741.pdf")
    assert dtype == DocumentType.DELIVERY_CHALLAN
    assert conf > 0.5


def test_classify_mill_test_cert_from_keywords():
    classifier = DocumentClassifier()
    text = (
        "MILL TEST CERTIFICATE\n"
        "Heat No: H-8821-A\n"
        "Chemical Composition: C: 0.06, Cr: 18.2\n"
        "Tensile Strength: 540 MPa"
    )
    dtype, conf = classifier.classify(text=text, filename="MTC-H8821.pdf")
    assert dtype == DocumentType.MILL_TEST_CERT
    assert conf > 0.5


def test_classify_commercial_invoice_from_fields():
    classifier = DocumentClassifier()
    fields = [
        ExtractedField.create(
            page_id="page_11111111111111111111111111111111",
            field_name="Invoice Number",
            field_value="INV-88992",
            raw_text="INV-88992",
            confidence=0.98,
            extraction_source=ExtractionSourceType.DIGITAL_TEXT,
        ),
        ExtractedField.create(
            page_id="page_11111111111111111111111111111111",
            field_name="Total Amount",
            field_value="531000.00",
            raw_text="531000.00",
            confidence=0.95,
            extraction_source=ExtractionSourceType.DIGITAL_TEXT,
        ),
    ]
    text = (
        "COMMERCIAL INVOICE\n"
        "Tax Invoice No: INV-88992\n"
        "GSTIN: 27AABCS1429B1Z8\n"
        "Taxable Value: 450000"
    )
    dtype, conf = classifier.classify(text=text, filename="INV-88992.pdf", extracted_fields=fields)
    assert dtype == DocumentType.COMMERCIAL_INVOICE
    assert conf > 0.5


def test_classify_empty_or_unrelated_returns_unclassified():
    classifier = DocumentClassifier()
    dtype, conf = classifier.classify(text="", filename="")
    assert dtype == DocumentType.UNCLASSIFIED
    assert conf == 0.0

    dtype, conf = classifier.classify(
        text="Random lorem ipsum text with no keywords", filename="notes.txt"
    )
    assert dtype == DocumentType.UNCLASSIFIED
