"""Contextual reasoning engine coordinating deterministic arithmetic and chronology verification."""

from __future__ import annotations

from typing import Any

from veritrace.capabilities.extraction.table_extractor import ExtractedTable
from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.forensic import EpistemicTier
from veritrace.domain.rules.arithmetic import (
    LineItemArithmeticRule,
    SubtotalTaxGrandTotalRule,
    TareNetGrossWeightRule,
)
from veritrace.domain.rules.base import ContextualRule, RuleEvaluationResult
from veritrace.domain.rules.chronology import (
    DocumentSequenceRule,
    PaymentTimelineRule,
    ValidityPeriodRule,
)


class ContextualReasoningEngine:
    """Orchestrates deterministic business rule validation across extracted fields,

    tabular line items, and temporal sequences in industrial documents.
    """

    def __init__(
        self,
        rules: list[ContextualRule] | None = None,
    ) -> None:
        self._rules = (
            rules
            if rules is not None
            else [
                LineItemArithmeticRule(),
                SubtotalTaxGrandTotalRule(),
                TareNetGrossWeightRule(),
                DocumentSequenceRule(),
                PaymentTimelineRule(),
                ValidityPeriodRule(),
            ]
        )

    @property
    def rules(self) -> list[ContextualRule]:
        """Return registered contextual rules."""
        return list(self._rules)

    def evaluate_line_items(
        self,
        tables_or_records: list[ExtractedTable] | list[dict[str, Any]],
    ) -> list[RuleEvaluationResult]:
        """Verify arithmetic integrity across line items in extracted tables or records.

        Checks: Quantity * Unit Rate * (1 - Discount/100) == Total Amount.
        """
        records: list[dict[str, Any]] = []
        for item in tables_or_records:
            if isinstance(item, ExtractedTable):
                records.extend(item.to_records())
            elif isinstance(item, dict):
                records.append(item)

        line_rule = next(
            (r for r in self._rules if isinstance(r, LineItemArithmeticRule)),
            LineItemArithmeticRule(),
        )

        results: list[RuleEvaluationResult] = []
        for rec in records:
            res = line_rule.evaluate(rec)
            if not res.passed:
                results.append(res)
        return results

    def create_proposal_from_result(self, res: RuleEvaluationResult) -> ForensicProposal:
        """Construct a ForensicProposal from a failed RuleEvaluationResult."""
        title_words = res.rule_name.replace("_", " ").title()
        return ForensicProposal(
            category=res.category,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=res.severity,
            title=f"Rule Inconsistency: {title_words}",
            narrative_explanation=res.explanation,
            confidence=1.0,
            measurements=res.measurements,
        )

    def evaluate_document(
        self,
        fields_or_dict: list[ExtractedField] | dict[str, Any],
        tables: list[ExtractedTable] | None = None,
    ) -> tuple[list[RuleEvaluationResult], list[ForensicProposal]]:
        """Run all applicable arithmetic and chronology rules against a document's extracted data.

        Args:
            fields_or_dict: ExtractedField entities or a flat dictionary of key-value pairs.
            tables: Optional extracted table structures for line item validation.

        Returns:
            Tuple of (list of all RuleEvaluationResults, list of generated ForensicProposals).
        """
        data: dict[str, Any] = {}
        if isinstance(fields_or_dict, dict):
            data = dict(fields_or_dict)
        elif isinstance(fields_or_dict, list):
            for f in fields_or_dict:
                if isinstance(f, ExtractedField):
                    data[f.field_name.lower().replace(" ", "_")] = f.field_value

        evaluations: list[RuleEvaluationResult] = []
        proposals: list[ForensicProposal] = []

        # 1. Evaluate tabular line items if tables provided
        if tables:
            line_results = self.evaluate_line_items(tables)
            for lr in line_results:
                evaluations.append(lr)
                if not lr.passed:
                    proposals.append(self.create_proposal_from_result(lr))

        # 2. Evaluate document summary rules (Subtotal/Tax/GrandTotal, Weights, Chronology)
        for rule in self._rules:
            if isinstance(rule, LineItemArithmeticRule):
                # Line items handled via tables/records
                continue

            res = rule.evaluate(data)
            evaluations.append(res)
            if not res.passed:
                proposals.append(self.create_proposal_from_result(res))

        return evaluations, proposals
