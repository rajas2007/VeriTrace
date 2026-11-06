"""Unit tests for deterministic procurement arithmetic and weight checksum rules."""

from veritrace.domain.enums.forensic import FindingCategory, FindingSeverity
from veritrace.domain.rules.arithmetic import (
    LineItemArithmeticRule,
    SubtotalTaxGrandTotalRule,
    TareNetGrossWeightRule,
    parse_numeric,
)


def test_parse_numeric_formats():
    """Verify parse_numeric cleanly strips currency, commas, and percentage."""
    assert parse_numeric(125) == 125.0
    assert parse_numeric(45.67) == 45.67
    assert parse_numeric("1,25,000.50") == 125000.50
    assert parse_numeric("₹ 45,000") == 45000.0
    assert parse_numeric("INR 10,500.25") == 10500.25
    assert parse_numeric("Rs. 500") == 500.0
    assert parse_numeric("$1,200.00") == 1200.0
    assert parse_numeric("18%") == 18.0
    assert parse_numeric("invalid_text") is None
    assert parse_numeric(None) is None


def test_line_item_arithmetic_rule_valid():
    """Verify matching line item calculations pass without discrepancies."""
    rule = LineItemArithmeticRule(tolerance=0.05)
    data = {
        "quantity": "25",
        "unit_rate": "1,000.00",
        "discount_pct": "10%",
        "total_amount": "22,500.00",  # 25 * 1000 * 0.9 = 22500
    }
    result = rule.evaluate(data)
    assert result.passed is True
    assert result.discrepancy == 0.0


def test_line_item_arithmetic_rule_discrepancy():
    """Verify mismatched line item triggers ARITHMETIC_MISMATCH failure."""
    rule = LineItemArithmeticRule(tolerance=0.50)
    data = {
        "quantity": "10",
        "unit_rate": "500.00",
        "total_amount": "6,500.00",  # Expected 5000, inflated to 6500
    }
    result = rule.evaluate(data)
    assert result.passed is False
    assert result.discrepancy == 1500.0
    assert result.expected_value == 5000.0
    assert result.observed_value == 6500.0
    assert result.category == FindingCategory.ARITHMETIC_MISMATCH
    assert result.severity == FindingSeverity.HIGH
    assert result.measurements["discrepancy"] == 1500.0


def test_subtotal_tax_grand_total_rule_valid():
    """Verify correct subtotal + GST calculations pass."""
    rule = SubtotalTaxGrandTotalRule(tolerance=0.50)
    data = {
        "subtotal": "1,00,000.00",
        "cgst": "9,000.00",
        "sgst": "9,000.00",
        "grand_total": "1,18,000.00",
    }
    result = rule.evaluate(data)
    assert result.passed is True


def test_subtotal_tax_grand_total_rule_mismatch():
    """Verify subtotal + tax mismatch generates failure."""
    rule = SubtotalTaxGrandTotalRule(tolerance=1.00)
    data = {
        "subtotal": "1,00,000.00",
        "tax_amount": "18,000.00",
        "grand_total": "1,30,000.00",  # Stated 130000 instead of 118000
    }
    result = rule.evaluate(data)
    assert result.passed is False
    assert result.discrepancy == 12000.0
    assert result.category == FindingCategory.ARITHMETIC_MISMATCH
    assert result.severity == FindingSeverity.HIGH


def test_tare_net_gross_weight_rule():
    """Verify tare + net == gross weight checks."""
    rule = TareNetGrossWeightRule(tolerance=0.01)

    # Valid check
    valid_data = {
        "gross_weight": "15.500",
        "tare_weight": "2.200",
        "net_weight": "13.300",
    }
    assert rule.evaluate(valid_data).passed is True

    # Invalid check
    invalid_data = {
        "gross_weight": "15.500",
        "tare_weight": "2.200",
        "net_weight": "14.500",  # Overstated net weight
    }
    result = rule.evaluate(invalid_data)
    assert result.passed is False
    assert result.category == FindingCategory.ARITHMETIC_MISMATCH
    assert result.discrepancy == 1.2
