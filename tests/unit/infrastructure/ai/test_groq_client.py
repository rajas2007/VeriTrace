"""Unit tests for Grounded Groq AI reasoning provider and privacy modes."""

from unittest.mock import MagicMock

from veritrace.capabilities.reasoning.synthesizer import LLMProviderProtocol, NarrativeSynthesizer
from veritrace.domain.entities.finding import Finding
from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory, FindingSeverity
from veritrace.domain.value_objects.identifiers import INV_PREFIX, generate_id
from veritrace.infrastructure.ai.groq_client import GroqLLMProvider, PrivacyMode


def test_groq_provider_protocol_conformance():
    """Verify GroqLLMProvider satisfies LLMProviderProtocol at runtime."""
    provider = GroqLLMProvider(privacy_mode=PrivacyMode.MODE_A_OFFLINE)
    assert isinstance(provider, LLMProviderProtocol)


def test_groq_provider_mode_a_offline():
    """Verify Mode A ensures strict offline operation and zero external requests."""
    provider = GroqLLMProvider(
        api_key="test_dummy_key_12345",
        privacy_mode=PrivacyMode.MODE_A_OFFLINE,
    )
    assert provider.is_available() is False
    assert provider.get_privacy_mode() == PrivacyMode.MODE_A_OFFLINE

    # Must return empty string immediately
    res = provider.generate_narrative("Evaluate forensic discrepancy")
    assert res == ""


def test_groq_provider_pii_redaction():
    """Verify sensitive Indian financial and identity numbers are redacted in Mode C."""
    provider = GroqLLMProvider(privacy_mode=PrivacyMode.MODE_C_REDACTED)

    raw_text = (
        "Vendor PAN is ABCDE1234F and GSTIN is 27ABCDE1234F1Z5. "
        "Examiner Aadhaar is 1234 5678 9012 and payment account is 9876543210123."
    )

    sanitized = provider.sanitize_payload(raw_text)

    assert "ABCDE1234F" not in sanitized
    assert "[REDACTED_PAN]" in sanitized
    assert "27ABCDE1234F1Z5" not in sanitized
    assert "[REDACTED_GSTIN]" in sanitized
    assert "1234 5678 9012" not in sanitized
    assert "[REDACTED_AADHAAR]" in sanitized
    assert "9876543210123" not in sanitized
    assert "[REDACTED_ACCOUNT_NO]" in sanitized


def test_groq_provider_mode_b_statistical_filtering():
    """Verify Mode B filters out arbitrary narrative lines and retains only statistical metrics."""
    provider = GroqLLMProvider(privacy_mode=PrivacyMode.MODE_B_STATISTICAL)

    raw_text = (
        "Company Name: Alpha Industrial Supplies Ltd.\n"
        "Metric: discrepancy_amount = 106200.0\n"
        "Supplier Address: Plot 42, Peenya Industrial Area, Bengaluru\n"
        "Confidence score: 0.98\n"
        "Severity tier: SUSPECTED_MANIPULATION\n"
        "Contact Person: Rajesh Sharma"
    )

    sanitized = provider.sanitize_payload(raw_text)

    assert "Alpha Industrial Supplies" not in sanitized
    assert "Peenya Industrial Area" not in sanitized
    assert "Rajesh Sharma" not in sanitized
    assert "Metric: discrepancy_amount = 106200.0" in sanitized
    assert "Confidence score: 0.98" in sanitized
    assert "Severity tier: SUSPECTED_MANIPULATION" in sanitized


def test_groq_provider_successful_chat_completion_and_audit():
    """Verify Groq chat completion parsing and audit logging."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "Observation: Metric disparity of 106,200 INR detected across PO and invoice."
    )
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.total_tokens = 42
    mock_client.chat.completions.create.return_value = mock_response

    audit_logs = []

    def audit_callback(entry):
        audit_logs.append(entry)

    provider = GroqLLMProvider(
        custom_client=mock_client,
        privacy_mode=PrivacyMode.MODE_C_REDACTED,
        audit_logger=audit_callback,
    )
    assert provider.is_available() is True

    result = provider.generate_narrative("Prompt with PAN ABCDE1234F")

    assert "106,200 INR" in result
    mock_client.chat.completions.create.assert_called_once()

    # Check that prompt was redacted before sending
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    messages = call_kwargs["messages"]
    user_prompt = messages[1]["content"]
    assert "[REDACTED_PAN]" in user_prompt
    assert "ABCDE1234F" not in user_prompt

    # Check audit log
    assert len(audit_logs) == 1
    assert audit_logs[0]["provider"] == "Groq"
    assert audit_logs[0]["status"] == "SUCCESS"
    assert audit_logs[0]["tokens_used"] == 42
    assert audit_logs[0]["latency_ms"] >= 0.0


def test_groq_provider_failure_and_audit():
    """Verify graceful handling when Groq API raises an exception."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = ConnectionError("Groq endpoint unreachable")

    audit_logs = []
    provider = GroqLLMProvider(
        custom_client=mock_client,
        privacy_mode=PrivacyMode.MODE_C_REDACTED,
        audit_logger=lambda e: audit_logs.append(e),
    )

    result = provider.generate_narrative("Analyze findings")
    assert result == ""  # Never crash; returns empty string

    assert len(audit_logs) == 1
    assert "FAILED" in audit_logs[0]["status"]
    assert "Groq endpoint unreachable" in audit_logs[0]["status"]


def test_narrative_synthesizer_groq_integration():
    """Verify NarrativeSynthesizer delegates to Groq and falls back to template on failure."""
    mock_provider = MagicMock(spec=GroqLLMProvider)
    mock_provider.generate_narrative.return_value = "Grounded AI explanation of financial variance."

    synthesizer = NarrativeSynthesizer(llm_provider=mock_provider)

    sample_finding = Finding.create(
        investigation_id=generate_id(INV_PREFIX),
        category=FindingCategory.CROSS_DOC_MISMATCH,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Billed quantity exceeds purchase order",
        narrative_explanation="Default explanation",
        confidence=0.95,
    )

    # 1. Successful generation via provider
    explanation = synthesizer.synthesize_finding_explanation(sample_finding)
    assert explanation == "Grounded AI explanation of financial variance."
    mock_provider.generate_narrative.assert_called_once()

    # 2. When provider returns empty string, fallback to offline template
    mock_provider.generate_narrative.return_value = ""
    fallback_explanation = synthesizer.synthesize_finding_explanation(sample_finding)
    assert fallback_explanation == "Default explanation"


def test_groq_test_connection_mode_a_airgap():
    """Verify test_connection in Mode A strictly preserves air gap without probing."""
    provider = GroqLLMProvider(
        api_key="test_airgap_key_12345",
        privacy_mode=PrivacyMode.MODE_A_OFFLINE,
    )
    success, msg = provider.test_connection()
    assert success is False
    assert "Mode A" in msg
    assert "prohibited" in msg


def test_groq_test_connection_no_key():
    """Verify test_connection fails cleanly when no key is provided."""
    provider = GroqLLMProvider(
        api_key=None,
        privacy_mode=PrivacyMode.MODE_B_STATISTICAL,
    )
    success, msg = provider.test_connection()
    assert success is False
    assert "No Groq API key" in msg


def test_groq_test_connection_probe_success():
    """Verify test_connection executes non-destructive models probe."""
    mock_client = MagicMock()
    mock_model = MagicMock()
    mock_model.id = "llama-3.3-70b-versatile"
    mock_client.models.list.return_value = MagicMock(data=[mock_model])

    provider = GroqLLMProvider(
        custom_client=mock_client,
        privacy_mode=PrivacyMode.MODE_B_STATISTICAL,
    )
    success, msg = provider.test_connection()
    assert success is True
    assert "Connection verified successfully" in msg
    assert "latency:" in msg
    mock_client.models.list.assert_called_once()


def test_groq_test_connection_auth_failure():
    """Verify test_connection reports 401 Unauthorized accurately."""
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("invalid_api_key (401 Unauthorized)")

    provider = GroqLLMProvider(
        custom_client=mock_client,
        privacy_mode=PrivacyMode.MODE_B_STATISTICAL,
    )
    success, msg = provider.test_connection()
    assert success is False
    assert "Invalid Groq API key" in msg


def test_ai_reasoning_finding_invariants():
    """Verify scientific invariant: AI cannot create, confirm, dismiss, or mutate findings."""
    mock_provider = MagicMock(spec=GroqLLMProvider)
    mock_provider.generate_narrative.return_value = (
        "CONFIRMED FRAUD: Suspect modified line quantity maliciously."
    )

    synthesizer = NarrativeSynthesizer(llm_provider=mock_provider)

    sample_finding = Finding.create(
        investigation_id=generate_id(INV_PREFIX),
        category=FindingCategory.CROSS_DOC_MISMATCH,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Discrepancy in item rate",
        narrative_explanation="Original deterministic explanation",
        confidence=0.92,
    )

    original_category = sample_finding.category
    original_severity = sample_finding.severity
    original_review_status = sample_finding.review_status
    original_tier = sample_finding.epistemic_tier

    explanation = synthesizer.synthesize_finding_explanation(sample_finding)

    # Narrative text may return the synthesized string
    assert "CONFIRMED FRAUD" in explanation

    # But finding domain entity invariants MUST remain 100% immutable
    assert sample_finding.category == original_category
    assert sample_finding.severity == original_severity
    assert sample_finding.review_status == original_review_status
    assert sample_finding.epistemic_tier == original_tier
