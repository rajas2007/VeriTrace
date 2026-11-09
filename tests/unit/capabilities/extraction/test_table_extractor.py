"""Unit tests for TableExtractor and ExtractedTable."""

import pytest

from veritrace.capabilities.extraction.table_extractor import (
    ExtractedTable,
    TableExtractor,
)
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import PAGE_PREFIX, generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken


def make_tok(text: str, ymin: float, xmin: float, ymax: float, xmax: float) -> ExtractedToken:
    """Helper to generate spatial token."""
    return ExtractedToken(
        token_id=f"tok_{text}",
        text=text,
        raw_text=text,
        normalized_bbox=NormalizedBoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax),
        confidence=0.95,
        page_number=1,
        source_type=ExtractionSourceType.DIGITAL_TEXT,
    )


@pytest.fixture
def bank_statement_tokens() -> list[ExtractedToken]:
    """Simulate extracted tokens for a 3-column bank statement transaction table."""
    # Column 0: Date [0.10, 0.25]
    # Column 1: Description [0.30, 0.60]
    # Column 2: Credit [0.65, 0.85]
    return [
        # Row 0: Headers
        make_tok("Date", 0.10, 0.10, 0.13, 0.25),
        make_tok("Description", 0.10, 0.30, 0.13, 0.55),
        make_tok("Credit", 0.10, 0.65, 0.13, 0.80),
        # Row 1: Txn 1
        make_tok("01/03/2026", 0.15, 0.10, 0.18, 0.25),
        make_tok("SALARY", 0.15, 0.30, 0.18, 0.42),
        make_tok("CREDIT", 0.15, 0.44, 0.18, 0.58),
        make_tok("85000", 0.15, 0.65, 0.18, 0.78),
        # Row 2: Txn 2
        make_tok("05/03/2026", 0.20, 0.10, 0.23, 0.25),
        make_tok("DIVIDEND", 0.20, 0.30, 0.23, 0.45),
        make_tok("CREDIT", 0.20, 0.47, 0.23, 0.58),
        make_tok("12000", 0.20, 0.65, 0.23, 0.78),
    ]


def test_extract_tables_from_tokens(bank_statement_tokens: list[ExtractedToken]):
    """Verify TableExtractor reconstructs columns, headers, and rows from tokens."""
    extractor = TableExtractor()
    tables = extractor.extract_tables_from_tokens(bank_statement_tokens, page_number=1)

    assert len(tables) == 1
    table = tables[0]
    assert isinstance(table, ExtractedTable)
    assert table.page_number == 1
    assert len(table.headers) == 3
    assert "Date" in table.headers[0]
    assert "Description" in table.headers[1]
    assert "Credit" in table.headers[2]

    # Verify rows
    assert len(table.rows) == 2
    # Row 1
    assert "01/03/2026" in table.rows[0][0]
    assert "SALARY CREDIT" in table.rows[0][1]
    assert "85000" in table.rows[0][2]
    # Row 2
    assert "05/03/2026" in table.rows[1][0]
    assert "DIVIDEND CREDIT" in table.rows[1][1]
    assert "12000" in table.rows[1][2]


def test_table_to_records(bank_statement_tokens: list[ExtractedToken]):
    """Verify to_records formats rows into list of dictionaries for cross-doc correlation."""
    extractor = TableExtractor()
    tables = extractor.extract_tables_from_tokens(bank_statement_tokens, page_number=1)
    records = tables[0].to_records()

    assert len(records) == 2
    assert records[0]["Date"] == "01/03/2026"
    assert records[0]["Description"] == "SALARY CREDIT"
    assert records[0]["Credit"] == "85000"

    assert records[1]["Date"] == "05/03/2026"
    assert records[1]["Description"] == "DIVIDEND CREDIT"
    assert records[1]["Credit"] == "12000"


def test_table_to_extracted_fields(bank_statement_tokens: list[ExtractedToken]):
    """Verify to_extracted_fields generates domain ExtractedField entities."""
    extractor = TableExtractor()
    tables = extractor.extract_tables_from_tokens(bank_statement_tokens, page_number=1)
    page_id = generate_id(PAGE_PREFIX)

    fields = tables[0].to_extracted_fields(page_id=page_id)
    assert len(fields) > 0
    for f in fields:
        assert isinstance(f, ExtractedField)
        assert f.page_id == page_id
        assert f.field_type == "table_cell"
        assert f.normalized_bbox is not None


def test_empty_tokens_returns_no_tables():
    """Verify empty tokens list gracefully returns empty tables list."""
    extractor = TableExtractor()
    assert extractor.extract_tables_from_tokens([], page_number=1) == []
