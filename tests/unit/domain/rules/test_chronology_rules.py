"""Unit tests for deterministic chronology and temporal consistency rules."""

from datetime import datetime

from veritrace.domain.enums.forensic import FindingCategory, FindingSeverity
from veritrace.domain.rules.chronology import (
    DocumentSequenceRule,
    PaymentTimelineRule,
    ValidityPeriodRule,
    parse_date,
)


def test_parse_date_formats():
    """Verify parse_date handles varied Indian and international date formats."""
    expected = datetime(2025, 10, 15)
    assert parse_date("2025-10-15") == expected
    assert parse_date("15/10/2025") == expected
    assert parse_date("15-10-2025") == expected
    assert parse_date("15 Oct 2025") == expected
    assert parse_date("15 October 2025") == expected
    assert parse_date("invalid_date") is None
    assert parse_date(None) is None


def test_document_sequence_rule_valid():
    """Verify normal forward order (PO -> Challan -> Invoice) passes."""
    rule = DocumentSequenceRule()
    data = {
        "po_date": "2025-01-10",
        "challan_date": "2025-01-15",
        "invoice_date": "2025-01-18",
    }
    result = rule.evaluate(data)
    assert result.passed is True


def test_document_sequence_reversal_po_challan():
    """Verify Challan dispatch date preceding PO issuance triggers failure."""
    rule = DocumentSequenceRule()
    data = {
        "po_date": "2025-02-01",
        "challan_date": "2025-01-20",  # 12 days before PO
        "invoice_date": "2025-02-05",
    }
    result = rule.evaluate(data)
    assert result.passed is False
    assert result.discrepancy == 12.0
    assert result.category == FindingCategory.TEMPORAL_CONTRADICTION
    assert result.severity == FindingSeverity.HIGH
    assert "precedes Purchase Order" in result.explanation


def test_payment_timeline_rule():
    """Verify payment due date logic."""
    rule = PaymentTimelineRule()

    # Valid: due date after invoice date
    assert rule.evaluate({"invoice_date": "2025-03-01", "due_date": "2025-03-31"}).passed is True

    # Invalid: due date before invoice date
    res = rule.evaluate({"invoice_date": "2025-03-15", "due_date": "2025-03-01"})
    assert res.passed is False
    assert res.category == FindingCategory.TEMPORAL_CONTRADICTION
    assert res.severity == FindingSeverity.HIGH


def test_validity_period_rule():
    """Verify credential / quote expiration checks."""
    rule = ValidityPeriodRule()

    # Valid
    assert rule.evaluate({"issue_date": "2025-01-01", "expiry_date": "2026-01-01"}).passed is True

    # Invalid (expired prior to issue)
    res = rule.evaluate({"issue_date": "2025-06-01", "expiry_date": "2025-05-01"})
    assert res.passed is False
    assert res.category == FindingCategory.TEMPORAL_CONTRADICTION
    assert res.severity == FindingSeverity.HIGH
