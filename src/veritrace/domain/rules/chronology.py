"""Deterministic chronology and temporal consistency rules for industrial procurement workflows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from veritrace.domain.enums.forensic import FindingCategory, FindingSeverity
from veritrace.domain.rules.base import ContextualRule, RuleEvaluationResult

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
)


def parse_date(value: Any) -> datetime | None:
    """Safely parse a datetime object from date, datetime, or diverse standard string formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    cleaned = str(value).strip()
    if not cleaned:
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


class DocumentSequenceRule(ContextualRule):
    """Verifies standard chronology: PO Date <= Challan Date <= Invoice Date."""

    @property
    def name(self) -> str:
        return "DOCUMENT_CHRONOLOGY_SEQUENCE"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.TEMPORAL_CONTRADICTION

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate dictionary with po_date, challan_date, and/or invoice_date."""
        po_dt = parse_date(data.get("po_date", data.get("purchase_order_date")))
        challan_dt = parse_date(data.get("challan_date", data.get("delivery_challan_date")))
        invoice_dt = parse_date(data.get("invoice_date", data.get("bill_date")))

        # Check 1: PO Date vs Challan Date
        if po_dt and challan_dt and challan_dt < po_dt:
            delta_days = (po_dt - challan_dt).days
            explanation = (
                f"Delivery Challan date ({challan_dt.strftime('%Y-%m-%d')}) precedes "
                f"Purchase Order date ({po_dt.strftime('%Y-%m-%d')}) by {delta_days} days. "
                "Inverted sequence indicates chronological manipulation or backdating."
            )
            measurements = {
                "po_date": po_dt.strftime("%Y-%m-%d"),
                "challan_date": challan_dt.strftime("%Y-%m-%d"),
                "reversal_days": delta_days,
            }
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=False,
                discrepancy=float(delta_days),
                expected_value=f">= {po_dt.strftime('%Y-%m-%d')}",
                observed_value=challan_dt.strftime("%Y-%m-%d"),
                explanation=explanation,
                severity=FindingSeverity.HIGH,
                measurements=measurements,
                affected_field_names=["po_date", "challan_date"],
            )

        # Check 2: PO Date vs Invoice Date
        if po_dt and invoice_dt and invoice_dt < po_dt:
            delta_days = (po_dt - invoice_dt).days
            explanation = (
                f"Tax Invoice date ({invoice_dt.strftime('%Y-%m-%d')}) precedes "
                f"Purchase Order date ({po_dt.strftime('%Y-%m-%d')}) by {delta_days} days. "
                "Billing issued prior to order authorization indicates date tampering."
            )
            measurements = {
                "po_date": po_dt.strftime("%Y-%m-%d"),
                "invoice_date": invoice_dt.strftime("%Y-%m-%d"),
                "reversal_days": delta_days,
            }
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=False,
                discrepancy=float(delta_days),
                expected_value=f">= {po_dt.strftime('%Y-%m-%d')}",
                observed_value=invoice_dt.strftime("%Y-%m-%d"),
                explanation=explanation,
                severity=FindingSeverity.HIGH,
                measurements=measurements,
                affected_field_names=["po_date", "invoice_date"],
            )

        # Check 3: Challan Date vs Invoice Date
        if challan_dt and invoice_dt and invoice_dt < challan_dt:
            delta_days = (challan_dt - invoice_dt).days
            explanation = (
                f"Invoice date ({invoice_dt.strftime('%Y-%m-%d')}) precedes "
                f"Challan date ({challan_dt.strftime('%Y-%m-%d')}) by {delta_days} days. "
                "Premature invoice generation detected."
            )
            measurements = {
                "challan_date": challan_dt.strftime("%Y-%m-%d"),
                "invoice_date": invoice_dt.strftime("%Y-%m-%d"),
                "reversal_days": delta_days,
            }
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=False,
                discrepancy=float(delta_days),
                expected_value=f">= {challan_dt.strftime('%Y-%m-%d')}",
                observed_value=invoice_dt.strftime("%Y-%m-%d"),
                explanation=explanation,
                severity=FindingSeverity.MEDIUM,
                measurements=measurements,
                affected_field_names=["challan_date", "invoice_date"],
            )

        return RuleEvaluationResult(
            rule_name=self.name,
            category=self.category,
            passed=True,
            explanation="Document chronology verified in valid forward sequence.",
            affected_field_names=["po_date", "challan_date", "invoice_date"],
        )


class PaymentTimelineRule(ContextualRule):
    """Verifies that Payment Due Date occurs on or after Invoice Date."""

    @property
    def name(self) -> str:
        return "PAYMENT_TIMELINE"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.TEMPORAL_CONTRADICTION

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate invoice_date and due_date."""
        invoice_dt = parse_date(data.get("invoice_date", data.get("bill_date")))
        due_dt = parse_date(data.get("due_date", data.get("payment_due_date")))

        if not invoice_dt or not due_dt:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                explanation="Missing invoice date or due date for payment timeline check.",
            )

        if due_dt < invoice_dt:
            delta_days = (invoice_dt - due_dt).days
            explanation = (
                f"Stated payment due date ({due_dt.strftime('%Y-%m-%d')}) precedes "
                f"invoice date ({invoice_dt.strftime('%Y-%m-%d')}) by {delta_days} days. "
                "Logically impossible credit term indicates data modification."
            )
            measurements = {
                "invoice_date": invoice_dt.strftime("%Y-%m-%d"),
                "due_date": due_dt.strftime("%Y-%m-%d"),
                "reversal_days": delta_days,
            }
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=False,
                discrepancy=float(delta_days),
                expected_value=f">= {invoice_dt.strftime('%Y-%m-%d')}",
                observed_value=due_dt.strftime("%Y-%m-%d"),
                explanation=explanation,
                severity=FindingSeverity.HIGH,
                measurements=measurements,
                affected_field_names=["invoice_date", "due_date"],
            )

        return RuleEvaluationResult(
            rule_name=self.name,
            category=self.category,
            passed=True,
            explanation="Payment due date timeline verified.",
            affected_field_names=["invoice_date", "due_date"],
        )


class ValidityPeriodRule(ContextualRule):
    """Verifies that an authorized credential or quote expiry date is after its issue date."""

    @property
    def name(self) -> str:
        return "VALIDITY_PERIOD"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.TEMPORAL_CONTRADICTION

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate issue_date and expiry_date."""
        issue_dt = parse_date(data.get("issue_date", data.get("valid_from")))
        expiry_dt = parse_date(
            data.get("expiry_date", data.get("valid_to", data.get("valid_thru")))
        )

        if not issue_dt or not expiry_dt:
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=True,
                explanation="Missing issue date or expiry date for validity period check.",
            )

        if expiry_dt < issue_dt:
            delta_days = (issue_dt - expiry_dt).days
            explanation = (
                f"Document expiration date ({expiry_dt.strftime('%Y-%m-%d')}) precedes "
                f"issuance date ({issue_dt.strftime('%Y-%m-%d')}) by {delta_days} days. "
                "Document expired prior to issue, indicating invalid or falsified credential."
            )
            measurements = {
                "issue_date": issue_dt.strftime("%Y-%m-%d"),
                "expiry_date": expiry_dt.strftime("%Y-%m-%d"),
                "reversal_days": delta_days,
            }
            return RuleEvaluationResult(
                rule_name=self.name,
                category=self.category,
                passed=False,
                discrepancy=float(delta_days),
                expected_value=f">= {issue_dt.strftime('%Y-%m-%d')}",
                observed_value=expiry_dt.strftime("%Y-%m-%d"),
                explanation=explanation,
                severity=FindingSeverity.HIGH,
                measurements=measurements,
                affected_field_names=["issue_date", "expiry_date"],
            )

        return RuleEvaluationResult(
            rule_name=self.name,
            category=self.category,
            passed=True,
            explanation="Validity period verified in valid chronological order.",
            affected_field_names=["issue_date", "expiry_date"],
        )
