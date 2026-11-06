"""Unit tests for NarrativeSynthesizer grounded explanation generation."""

from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.capabilities.reasoning.synthesizer import (
    LLMProviderProtocol,
    NarrativeSynthesizer,
)
from veritrace.domain.entities.finding import Finding
from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory, FindingSeverity
from veritrace.domain.value_objects.identifiers import FND_PREFIX, INV_PREFIX, generate_id, utc_now


class DummyMockLLM(LLMProviderProtocol):
    """Mock LLM provider returning simulated grounded summary."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def generate_narrative(self, prompt: str, system_prompt: str | None = None) -> str:
        if self.should_fail:
            raise RuntimeError("Network offline")
        return "Grounded narrative synthesized from verified numerical metrics."


def test_synthesizer_offline_template():
    """Verify synthesizer produces factual explanation without LLM."""
    synthesizer = NarrativeSynthesizer(llm_provider=None)

    proposal = ForensicProposal(
        category=FindingCategory.ARITHMETIC_MISMATCH,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Grand Total Mismatch",
        narrative_explanation="Subtotal + tax does not equal total.",
        confidence=1.0,
        measurements={
            "expected_total": 59000.0,
            "observed_total": 70000.0,
            "discrepancy": 11000.0,
        },
    )

    explanation = synthesizer.synthesize_finding_explanation(proposal)
    assert "computed value is 59000.0" in explanation
    assert "records 70000.0" in explanation
    assert "diff: 11000.0" in explanation


def test_synthesizer_with_llm_provider():
    """Verify synthesizer calls LLM provider when configured."""
    mock_llm = DummyMockLLM()
    synthesizer = NarrativeSynthesizer(llm_provider=mock_llm)

    proposal = ForensicProposal(
        category=FindingCategory.TEMPORAL_CONTRADICTION,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Challan Reversal",
        narrative_explanation="Challan precedes PO.",
        confidence=1.0,
        measurements={"reversal_days": 15},
    )

    explanation = synthesizer.synthesize_finding_explanation(proposal)
    assert explanation == "Grounded narrative synthesized from verified numerical metrics."


def test_synthesizer_llm_failure_falls_back_to_offline_template():
    """Verify synthesizer falls back smoothly to offline template on LLM failure."""
    failing_llm = DummyMockLLM(should_fail=True)
    synthesizer = NarrativeSynthesizer(llm_provider=failing_llm)

    proposal = ForensicProposal(
        category=FindingCategory.TEMPORAL_CONTRADICTION,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Challan Reversal",
        narrative_explanation="Challan precedes PO.",
        confidence=1.0,
        measurements={"reversal_days": 15},
    )

    explanation = synthesizer.synthesize_finding_explanation(proposal)
    assert "event sequence is inverted by 15 day(s)" in explanation


def test_synthesizer_executive_summary():
    """Verify executive summary groups multiple finding categories."""
    synthesizer = NarrativeSynthesizer()

    f1 = Finding(
        id=generate_id(FND_PREFIX),
        investigation_id=generate_id(INV_PREFIX),
        category=FindingCategory.ARITHMETIC_MISMATCH,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Math Error",
        narrative_explanation="Math calculation mismatch.",
        created_at=utc_now(),
    )
    f2 = Finding(
        id=generate_id(FND_PREFIX),
        investigation_id=generate_id(INV_PREFIX),
        category=FindingCategory.SIGNATURE_VERIFICATION,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.MEDIUM,
        title="Signature Discrepancy",
        narrative_explanation="Optical stroke variance observed.",
        created_at=utc_now(),
    )

    summary = synthesizer.synthesize_executive_summary([f1, f2])
    assert "2 forensic finding(s)" in summary
    assert "Arithmetic Discrepancies" in summary
    assert "Signature Verification Findings" in summary
    assert "human investigator" in summary
