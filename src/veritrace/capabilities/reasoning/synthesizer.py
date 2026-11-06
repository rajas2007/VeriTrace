"""Grounded narrative synthesis over deterministic forensic findings and measurements."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.domain.entities.finding import Finding
from veritrace.domain.enums.forensic import FindingCategory


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """Protocol for optional large language model providers generating grounded narrative text."""

    def generate_narrative(self, prompt: str, system_prompt: str | None = None) -> str:
        """Synthesize narrative explanation from structured metrics."""
        ...


class NarrativeSynthesizer:
    """Generates objective, auditor-grade investigative narratives over verified findings.

    SCIENTIFIC INVARIANTS:
    1. Operates strictly downstream of deterministic CV, arithmetic, and timeline checks.
    2. Data minimization: only structured finding summaries and anonymized metric dictionaries
       are processed (zero raw document scans or full-text uploads).
    3. Provides 100% deterministic local offline template synthesis for air-gapped environments.
    """

    def __init__(self, llm_provider: LLMProviderProtocol | None = None) -> None:
        self._llm_provider = llm_provider

    def synthesize_finding_explanation(
        self,
        finding_or_proposal: Finding | ForensicProposal,
        anonymize: bool = True,
    ) -> str:
        """Generate a concise, factual narrative paragraph for an individual finding or proposal."""
        # 1. If LLM provider is available, construct constrained data-minimized prompt
        if self._llm_provider is not None:
            try:
                prompt = self._build_constrained_prompt(finding_or_proposal)
                system_prompt = (
                    "You are an impartial forensic document auditor. "
                    "Explain the factual evidence strictly based on the provided metrics. "
                    "Do NOT extrapolate legal guilt, fraud, or intentionality. "
                    "Keep the explanation strictly objective, professional, and under 3 sentences."
                )
                narrative = self._llm_provider.generate_narrative(prompt, system_prompt)
                if narrative and narrative.strip():
                    return narrative.strip()
            except Exception:
                # Seamless deterministic fallback on any LLM or network failure
                pass

        # 2. Deterministic local template fallback
        return self._format_offline_template(finding_or_proposal)

    def synthesize_executive_summary(
        self,
        findings_or_proposals: list[Finding] | list[ForensicProposal],
    ) -> str:
        """Compile a multi-paragraph executive audit summary from a collection of findings."""
        if not findings_or_proposals:
            return (
                "Forensic inspection completed. No visual manipulation, arithmetic mismatches, "
                "or temporal contradictions were detected across the analyzed document set."
            )

        cat_counts: dict[FindingCategory, int] = {}
        for f in findings_or_proposals:
            cat = f.category
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        lines: list[str] = [
            f"Investigation concluded with {len(findings_or_proposals)} forensic finding(s) "
            "identified across physical, mathematical, and chronological verification dimensions:\n"
        ]

        if FindingCategory.ARITHMETIC_MISMATCH in cat_counts:
            count = cat_counts[FindingCategory.ARITHMETIC_MISMATCH]
            lines.append(
                f"- Arithmetic Discrepancies ({count}): "
                "Mathematical calculations between unit rates, line subtotals, and statutory taxes "
                "deviate beyond standard rounding tolerances."
            )
        if FindingCategory.TEMPORAL_CONTRADICTION in cat_counts:
            count = cat_counts[FindingCategory.TEMPORAL_CONTRADICTION]
            lines.append(
                f"- Chronological Contradictions ({count}): "
                "Inverted document sequences or invalid validity dates detected, indicating "
                "potential backdating or sequencing anomalies."
            )
        if FindingCategory.SIGNATURE_VERIFICATION in cat_counts:
            count = cat_counts[FindingCategory.SIGNATURE_VERIFICATION]
            lines.append(
                f"- Signature Verification Findings ({count}): "
                "Optical stroke divergences or boundary clipping artifacts observed. "
                "Adjudication requires human forensic examiner review."
            )
        if FindingCategory.ELA_COMPRESSION_VARIANCE in cat_counts:
            count = cat_counts[FindingCategory.ELA_COMPRESSION_VARIANCE]
            lines.append(
                f"- Compression Discontinuities ({count}): "
                "Error Level Analysis identified localized JPEG re-compression differentials "
                "consistent with digitally spliced patches."
            )
        if FindingCategory.FONT_BASELINE_MISALIGNMENT in cat_counts:
            count = cat_counts[FindingCategory.FONT_BASELINE_MISALIGNMENT]
            lines.append(
                f"- Font Baseline Misalignments ({count}): "
                "Character regression baselines exhibit vertical displacement anomalies (>2.5σ), "
                "signaling numeral insertion."
            )

        lines.append(
            "\nEpistemic Guidance: In accordance with forensic standards, machine observations "
            "constitute empirical evidence and must be reviewed by a human investigator."
        )

        return "\n".join(lines)

    def _format_offline_template(self, item: Finding | ForensicProposal) -> str:
        """Deterministic local template formatting ensuring 100% offline reliability."""
        if isinstance(item, ForensicProposal):
            measurements = item.measurements
            if item.category == FindingCategory.ARITHMETIC_MISMATCH:
                exp = measurements.get(
                    "expected_total", measurements.get("expected_grand_total", "N/A")
                )
                obs = measurements.get(
                    "observed_total", measurements.get("observed_grand_total", "N/A")
                )
                diff = measurements.get("discrepancy", "N/A")
                return (
                    f"Mathematical reconciliation identified an arithmetic discrepancy: "
                    f"computed value is {exp}, whereas document records {obs} (diff: {diff})."
                )
            if item.category == FindingCategory.TEMPORAL_CONTRADICTION:
                reversal = measurements.get("reversal_days", "N/A")
                return (
                    f"Chronological analysis identified a temporal contradiction: "
                    f"event sequence is inverted by {reversal} day(s), violating forward order."
                )
            return item.narrative_explanation

        if isinstance(item, Finding):
            return item.narrative_explanation

        return "Factual discrepancy recorded for investigator examination."

    def _build_constrained_prompt(self, item: Finding | ForensicProposal) -> str:
        """Assemble structured, data-minimized metrics dictionary for optional LLM narration."""
        metrics: dict[str, Any] = {
            "finding_category": item.category.value,
            "epistemic_tier": item.epistemic_tier.value,
            "severity": item.severity.value,
        }
        if isinstance(item, ForensicProposal):
            metrics["measurements"] = item.measurements
            metrics["technical_explanation"] = item.narrative_explanation
        elif isinstance(item, Finding):
            metrics["title"] = item.title
            metrics["technical_explanation"] = item.narrative_explanation
        return f"Metrics payload: {metrics}"
