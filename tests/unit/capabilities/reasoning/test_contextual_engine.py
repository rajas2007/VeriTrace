"""Unit tests for ContextualReasoningEngine coordination."""

from veritrace.capabilities.extraction.table_extractor import ExtractedTable, TableCell
from veritrace.capabilities.reasoning.contextual_engine import ContextualReasoningEngine
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.forensic import FindingCategory
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import FLD_PREFIX, PAGE_PREFIX, generate_id


def test_engine_evaluates_tabular_line_items():
    """Verify engine runs LineItemArithmeticRule across ExtractedTable cells."""
    engine = ContextualReasoningEngine()

    cells = [
        TableCell(
            row_index=0,
            col_index=0,
            text="Item 1",
            normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.15, xmax=0.3),
        ),
        TableCell(
            row_index=0,
            col_index=1,
            text="10",
            normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.3, ymax=0.15, xmax=0.4),
        ),
        TableCell(
            row_index=0,
            col_index=2,
            text="250.00",
            normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.4, ymax=0.15, xmax=0.6),
        ),
        TableCell(
            row_index=0,
            col_index=3,
            text="3,500.00",
            normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.6, ymax=0.15, xmax=0.8),
        ),  # Inflated! (expected 2500)
    ]
    table = ExtractedTable(
        table_index=0,
        page_number=1,
        normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.5, xmax=0.9),
        headers=["Description", "quantity", "unit_rate", "total_amount"],
        rows=[["Item 1", "10", "250.00", "3,500.00"]],
        cells=cells,
    )

    failures = engine.evaluate_line_items([table])
    assert len(failures) == 1
    assert failures[0].passed is False
    assert failures[0].discrepancy == 1000.0
    proposal = engine.create_proposal_from_result(failures[0])
    assert proposal is not None
    assert proposal.category == FindingCategory.ARITHMETIC_MISMATCH


def test_engine_evaluates_document_fields_and_generates_proposals():
    """Verify engine flags arithmetic and chronology discrepancies in document fields."""
    engine = ContextualReasoningEngine()

    page_id = generate_id(PAGE_PREFIX)
    fields = [
        ExtractedField(
            id=generate_id(FLD_PREFIX),
            page_id=page_id,
            field_name="subtotal",
            field_value="50,000.00",
            raw_text="50,000.00",
            confidence=0.99,
        ),
        ExtractedField(
            id=generate_id(FLD_PREFIX),
            page_id=page_id,
            field_name="tax_amount",
            field_value="9,000.00",
            raw_text="9,000.00",
            confidence=0.98,
        ),
        ExtractedField(
            id=generate_id(FLD_PREFIX),
            page_id=page_id,
            field_name="grand_total",
            field_value="70,000.00",  # Mismatch! (expected 59000)
            raw_text="70,000.00",
            confidence=0.99,
        ),
        ExtractedField(
            id=generate_id(FLD_PREFIX),
            page_id=page_id,
            field_name="po_date",
            field_value="2025-05-10",
            raw_text="2025-05-10",
            confidence=0.95,
        ),
        ExtractedField(
            id=generate_id(FLD_PREFIX),
            page_id=page_id,
            field_name="challan_date",
            field_value="2025-04-15",  # Reversal!
            raw_text="2025-04-15",
            confidence=0.95,
        ),
    ]

    evaluations, proposals = engine.evaluate_document(fields)

    # Should detect 2 discrepancies: arithmetic mismatch and temporal contradiction
    assert len(proposals) == 2
    categories = {p.category for p in proposals}
    assert FindingCategory.ARITHMETIC_MISMATCH in categories
    assert FindingCategory.TEMPORAL_CONTRADICTION in categories
