"""Unit tests for IBM Docling layout extraction adapter."""

import uuid
from pathlib import Path

from veritrace.capabilities.extraction.docling_adapter import (
    DoclingDocumentResult,
    DoclingLayoutAdapter,
)
from veritrace.capabilities.extraction.table_extractor import ExtractedTable


def test_docling_adapter_fallback_when_unavailable(tmp_path: Path):
    """Verify clean diagnostic DoclingDocumentResult when Docling is not installed."""
    dummy_file = tmp_path / "sample.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 test")

    adapter = DoclingLayoutAdapter()
    adapter._custom_parser = None

    if not adapter.is_available():
        res = adapter.parse_document(dummy_file)
        assert isinstance(res, DoclingDocumentResult)
        assert res.is_fallback is True
        assert len(res.elements) == 0
        assert len(res.tables) == 0
        assert len(res.warnings) > 0
        assert "not installed" in res.warnings[0].lower() or "bypassed" in res.warnings[0].lower()


def test_docling_adapter_with_custom_parser(tmp_path: Path):
    """Verify parsing layout elements, tables, and reading order."""
    dummy_file = tmp_path / "sample_contract.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 content")

    def mock_parser(path: Path):
        return {
            "elements": [
                {
                    "text": "INDUSTRIAL PROCUREMENT AGREEMENT",
                    "element_type": "header",
                    "page_number": 1,
                    "bbox": {"ymin": 0.05, "xmin": 0.1, "ymax": 0.12, "xmax": 0.9},
                },
                {
                    "text": "1. Scope of Supply: Stainless Steel Tubes grade 316L.",
                    "element_type": "paragraph",
                    "page_number": 1,
                    "bbox": {"ymin": 0.15, "xmin": 0.1, "ymax": 0.22, "xmax": 0.9},
                },
            ],
            "tables": [
                {
                    "page_number": 1,
                    "headers": ["Item", "Quantity (KG)", "Unit Rate (INR)", "Total"],
                    "rows": [
                        ["SS 316L Plates", "1000", "450.00", "450000.00"],
                    ],
                }
            ],
        }

    adapter = DoclingLayoutAdapter(custom_parser=mock_parser)
    assert adapter.is_available() is True

    res = adapter.parse_document(dummy_file)

    assert isinstance(res, DoclingDocumentResult)
    assert res.is_fallback is False
    assert len(res.elements) == 2
    assert len(res.tables) == 1
    assert "INDUSTRIAL PROCUREMENT AGREEMENT" in res.reading_order_text
    assert "Scope of Supply" in res.reading_order_text

    # Verify table conversion
    tbl = res.tables[0]
    assert isinstance(tbl, ExtractedTable)
    assert tbl.headers == ["Item", "Quantity (KG)", "Unit Rate (INR)", "Total"]
    assert len(tbl.rows) == 1
    assert tbl.rows[0][0] == "SS 316L Plates"
    assert tbl.rows[0][1] == "1000"

    # Verify table to records
    records = tbl.to_records()
    assert len(records) == 1
    assert records[0]["Item"] == "SS 316L Plates"
    assert records[0]["Total"] == "450000.00"

    # Verify table to extracted fields
    fields = tbl.to_extracted_fields(page_id=f"page_{uuid.uuid4().hex}")
    assert len(fields) == 4
    assert any(
        f.field_name == "table[0].row[0].Item" and f.field_value == "SS 316L Plates" for f in fields
    )
    assert any(
        f.field_name == "table[0].row[0].Total" and f.field_value == "450000.00" for f in fields
    )
