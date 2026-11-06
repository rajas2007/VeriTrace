"""Deterministic arithmetic and mathematical checksum rules for procurement and logistics."""

from __future__ import annotations

import re
from typing import Any

from veritrace.domain.enums.forensic import FindingCategory, FindingSeverity
from veritrace.domain.rules.base import ContextualRule, RuleEvaluationResult

_CURRENCY_PATTERN = re.compile(r"[₹$€£\s]|(?:INR|Rs\.?|EUR|USD|GBP)", re.IGNORECASE)


def parse_numeric(value: Any) -> float | None:
    """Safely parse a numerical float value from int, float, or formatted currency string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = str(value).strip()
    if not cleaned:
        return None

    # Remove currency abbreviations, symbols, and spaces
    cleaned = _CURRENCY_PATTERN.sub("", cleaned)
    # Remove commas
    cleaned = cleaned.replace(",", "")

    # Handle percentage
    if cleaned.endswith("%"):
        try:
            return float(cleaned[:-1].strip())
        except ValueError:
            return None

    try:
        return float(cleaned)
    except ValueError:
        return None


class LineItemArithmeticRule(ContextualRule):
    """Verifies that line item amount equals Quantity * Unit Rate * (1 - Discount/100)."""

    def __init__(self, tolerance: float = 0.50) -> None:
        self._tolerance = tolerance

    @property
    def name(self) -> str:
        return "LINE_ITEM_ARITHMETIC"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.ARITHMETIC_MISMATCH

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate line item dictionary containing quantity, unit_rate, and total_amount."""
        qty_val = (
            data.get("quantity") if "quantity" in data else data.get("qty", data.get("Quantity"))
        )
        rate_val = (
            data.get("unit_rate")
            if "unit_rate" in data
            else data.get("rate", data.get("price", data.get("Unit Rate")))
        )
        total_val = (
            data.get("total_amount")
            if "total_amount" in data
            else data.get("amount", data.get("total", data.get("Line Total")))
        )
        discount_val = (
            data.get("discount_pct") if "discount_pct" in data else data.get("discount", 0.0)
        )

        qty = parse_numeric(qty_val)
        rate = parse_numeric(rate_val)
        observed_total = parse_numeric(total_val)
        discount = parse_numeric(discount_val) or 0.0

        if qty is None or rate is None or observed_total is None:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                explanation="Missing quantity, rate, or total for line item arithmetic check.",
            )

        expected_total = qty * rate * (1.0 - (discount / 100.0))
        discrepancy = abs(observed_total - expected_total)

        if discrepancy <= self._tolerance:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                expected_value=round(expected_total, 2),
                observed_value=round(observed_total, 2),
                explanation="Line item arithmetic verified.",
                affected_field_names=["quantity", "unit_rate", "total_amount"],
            )

        # Mismatch detected
        severity = FindingSeverity.HIGH if discrepancy > 50.0 else FindingSeverity.MEDIUM
        explanation = (
            f"Line item amount mismatch: expected {expected_total:.2f}, "
            f"observed {observed_total:.2f} (diff: {discrepancy:.2f})"
        )
        measurements = {
            "quantity": qty,
            "unit_rate": rate,
            "discount_pct": discount,
            "expected_total": round(expected_total, 2),
            "observed_total": round(observed_total, 2),
            "discrepancy": round(discrepancy, 2),
        }

        return RuleEvaluationResult(
            rule_name=self.name,
            category=self.category,
            passed=False,
            discrepancy=round(discrepancy, 2),
            expected_value=round(expected_total, 2),
            observed_value=round(observed_total, 2),
            explanation=explanation,
            severity=severity,
            measurements=measurements,
            affected_field_names=["quantity", "unit_rate", "total_amount"],
        )


class SubtotalTaxGrandTotalRule(ContextualRule):
    """Verifies that Grand Total equals Subtotal + Taxes (CGST + SGST or IGST or Tax Amount)."""

    def __init__(self, tolerance: float = 1.00) -> None:
        self._tolerance = tolerance

    @property
    def name(self) -> str:
        return "SUBTOTAL_TAX_GRAND_TOTAL"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.ARITHMETIC_MISMATCH

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate procurement summary dictionary."""
        subtotal_val = data.get("subtotal", data.get("sub_total", data.get("taxable_value")))
        grand_total_val = data.get("grand_total", data.get("total_amount", data.get("total")))

        subtotal = parse_numeric(subtotal_val)
        observed_grand_total = parse_numeric(grand_total_val)

        if subtotal is None or observed_grand_total is None:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                explanation="Missing subtotal or grand total in document summary.",
            )

        # Sum of taxes: either single tax amount or broken down into CGST, SGST, IGST
        tax_val = data.get("tax_amount", data.get("tax", data.get("total_tax")))
        cgst_val = data.get("cgst", data.get("cgst_amount"))
        sgst_val = data.get("sgst", data.get("sgst_amount"))
        igst_val = data.get("igst", data.get("igst_amount"))

        tax = parse_numeric(tax_val)
        cgst = parse_numeric(cgst_val) or 0.0
        sgst = parse_numeric(sgst_val) or 0.0
        igst = parse_numeric(igst_val) or 0.0

        if tax is not None:
            total_tax = tax
        elif cgst > 0.0 or sgst > 0.0 or igst > 0.0:
            total_tax = cgst + sgst + igst
        else:
            total_tax = 0.0

        expected_grand_total = subtotal + total_tax
        discrepancy = abs(observed_grand_total - expected_grand_total)

        if discrepancy <= self._tolerance:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                expected_value=round(expected_grand_total, 2),
                observed_value=round(observed_grand_total, 2),
                explanation="Subtotal, tax, and grand total arithmetic verified.",
                affected_field_names=["subtotal", "tax_amount", "grand_total"],
            )

        severity = FindingSeverity.HIGH if discrepancy > 50.0 else FindingSeverity.MEDIUM
        explanation = (
            f"Grand total mismatch: expected {expected_grand_total:.2f}, "
            f"observed {observed_grand_total:.2f} (diff: {discrepancy:.2f})"
        )
        measurements = {
            "subtotal": subtotal,
            "total_tax": total_tax,
            "expected_grand_total": round(expected_grand_total, 2),
            "observed_grand_total": round(observed_grand_total, 2),
            "discrepancy": round(discrepancy, 2),
        }

        return RuleEvaluationResult(
            rule_name=self.name,
            category=self.category,
            passed=False,
            discrepancy=round(discrepancy, 2),
            expected_value=round(expected_grand_total, 2),
            observed_value=round(observed_grand_total, 2),
            explanation=explanation,
            severity=severity,
            measurements=measurements,
            affected_field_names=["subtotal", "tax_amount", "grand_total"],
        )


class TareNetGrossWeightRule(ContextualRule):
    """Verifies that Net Weight equals Gross Weight - Tare Weight in logistics/freight records."""

    def __init__(self, tolerance: float = 0.10) -> None:
        self._tolerance = tolerance

    @property
    def name(self) -> str:
        return "TARE_NET_GROSS_WEIGHT"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.ARITHMETIC_MISMATCH

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate weight reconciliation fields."""
        gross_val = data.get("gross_weight", data.get("gross_wt"))
        tare_val = data.get("tare_weight", data.get("tare_wt"))
        net_val = data.get("net_weight", data.get("net_wt"))

        gross = parse_numeric(gross_val)
        tare = parse_numeric(tare_val)
        observed_net = parse_numeric(net_val)

        if gross is None or tare is None or observed_net is None:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                explanation="Missing gross, tare, or net weight fields.",
            )

        expected_net = gross - tare
        discrepancy = abs(observed_net - expected_net)

        if discrepancy <= self._tolerance:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                expected_value=round(expected_net, 3),
                observed_value=round(observed_net, 3),
                explanation="Weight reconciliation verified.",
                affected_field_names=["gross_weight", "tare_weight", "net_weight"],
            )

        severity = FindingSeverity.HIGH if discrepancy > 5.0 else FindingSeverity.MEDIUM
        explanation = (
            f"Weight mismatch: expected net {expected_net:.3f}, "
            f"observed {observed_net:.3f} (diff: {discrepancy:.3f})"
        )
        measurements = {
            "gross_weight": gross,
            "tare_weight": tare,
            "expected_net": round(expected_net, 3),
            "observed_net": round(observed_net, 3),
            "discrepancy": round(discrepancy, 3),
        }

        return RuleEvaluationResult(
            rule_name=self.name,
            category=self.category,
            passed=False,
            discrepancy=round(discrepancy, 3),
            expected_value=round(expected_net, 3),
            observed_value=round(observed_net, 3),
            explanation=explanation,
            severity=severity,
            measurements=measurements,
            affected_field_names=["gross_weight", "tare_weight", "net_weight"],
        )
