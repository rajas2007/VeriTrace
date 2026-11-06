"""Base contracts and evaluation results for deterministic contextual business rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from veritrace.domain.enums.forensic import FindingCategory, FindingSeverity


@dataclass(slots=True)
class RuleEvaluationResult:
    """Quantitative outcome of executing a deterministic verification rule."""

    rule_name: str
    category: FindingCategory
    passed: bool
    discrepancy: float = 0.0
    expected_value: Any = None
    observed_value: Any = None
    explanation: str = ""
    severity: FindingSeverity = FindingSeverity.MEDIUM
    measurements: dict[str, Any] = field(default_factory=dict)
    affected_field_names: list[str] = field(default_factory=list)


@runtime_checkable
class ContextualRule(Protocol):
    """Protocol for deterministic domain rules validating arithmetic and chronology."""

    @property
    def name(self) -> str:
        """Unique rule identifier."""
        ...

    @property
    def category(self) -> FindingCategory:
        """Forensic finding category this rule verifies."""
        ...

    def evaluate(self, data: dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate input key-value fields or records against the rule."""
        ...
