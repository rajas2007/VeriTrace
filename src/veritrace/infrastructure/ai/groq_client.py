"""Grounded Groq AI reasoning provider implementing LLMProviderProtocol.

Operates strictly downstream of deterministic computer vision and arithmetic checks,
enforcing three-tier privacy modes, data minimization, and audit logging.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections.abc import Callable
from typing import Any

from veritrace.domain.enums.investigation import PrivacyMode

logger = logging.getLogger("veritrace.infrastructure.ai.groq_client")

try:
    from groq import Groq  # type: ignore[import-untyped]

    _GROQ_AVAILABLE = True
except (ImportError, Exception):
    Groq = None  # type: ignore[misc,assignment]
    _GROQ_AVAILABLE = False


# Redaction patterns for sensitive enterprise identifiers
_REDACTION_PATTERNS = [
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[REDACTED_PAN]"),
    (re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][Z][0-9A-Z]\b"), "[REDACTED_GSTIN]"),
    (re.compile(r"\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b"), "[REDACTED_AADHAAR]"),
    (re.compile(r"\b[0-9]{9,18}\b"), "[REDACTED_ACCOUNT_NO]"),
]


class GroqLLMProvider:
    """Grounded Cloud LLM provider connecting to Groq API.

    Implements LLMProviderProtocol while strictly enforcing data minimization,
    privacy modes, request timeouts, and audit trail records.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "llama-3.3-70b-versatile",
        privacy_mode: PrivacyMode = PrivacyMode.MODE_A_OFFLINE,
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
        custom_client: Any | None = None,
        audit_logger: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._explicit_api_key = api_key
        self._model_name = model_name
        self._privacy_mode = privacy_mode
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._custom_client = custom_client
        self._audit_logger = audit_logger
        self._client: Any = None

        self._init_client()

    def _get_api_key(self) -> str | None:
        """Resolve API key from parameter or environment without storing in plaintext logs."""
        return self._explicit_api_key or os.environ.get("GROQ_API_KEY")

    def _init_client(self) -> None:
        """Initialize Groq API client if available and enabled."""
        if self._custom_client is not None:
            self._client = self._custom_client
            return

        if self._privacy_mode == PrivacyMode.MODE_A_OFFLINE:
            # Mode A guarantees zero external connections
            self._client = None
            return

        api_key = self._get_api_key()
        if not api_key or not _GROQ_AVAILABLE or Groq is None:
            self._client = None
            return

        try:
            self._client = Groq(
                api_key=api_key, timeout=self._timeout_seconds, max_retries=self._max_retries
            )
        except Exception as exc:
            logger.warning("Failed to initialize Groq client: %s", exc)
            self._client = None

    def is_available(self) -> bool:
        """Return True if client is initialized and authorized under active privacy mode."""
        if self._privacy_mode == PrivacyMode.MODE_A_OFFLINE:
            return False
        return self._client is not None

    def test_connection(self) -> tuple[bool, str]:
        """Test API connectivity and credential validity without generating paid tokens.

        Returns:
            Tuple of (success_boolean, status_message).
        """
        if self._privacy_mode == PrivacyMode.MODE_A_OFFLINE:
            return (
                False,
                "Privacy Mode A is active (100% offline air-gapped). "
                "Network connections are prohibited.",
            )

        if not self._get_api_key() and self._custom_client is None:
            return False, "No Groq API key configured. Please enter a valid API key."

        if not _GROQ_AVAILABLE or Groq is None:
            return False, "Groq Python SDK is not installed on this host."

        start_time = time.time()
        try:
            self._init_client()
            if self._client is None:
                return False, "Groq client initialization failed."

            # Query models endpoint to test credentials with zero prompt token charge
            models_page = self._client.models.list()
            latency_ms = round((time.time() - start_time) * 1000, 1)
            model_ids = [m.id for m in getattr(models_page, "data", [])]
            count_str = f"{len(model_ids)} models available" if model_ids else "API responding"
            return True, f"Connection verified successfully ({count_str}, latency: {latency_ms}ms)."
        except Exception as exc:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            err_str = str(exc)
            if "invalid_api_key" in err_str.lower() or "401" in err_str:
                return False, "Authentication failed: Invalid Groq API key (401 Unauthorized)."
            if "rate_limit" in err_str.lower() or "429" in err_str:
                return False, "Rate limit reached: Too many requests (429)."
            if "timeout" in err_str.lower():
                return False, f"Request timed out after {self._timeout_seconds}s."
            return False, f"Connection error ({type(exc).__name__}): {err_str}"

    def get_privacy_mode(self) -> PrivacyMode:
        """Return active privacy mode."""
        return self._privacy_mode

    def set_privacy_mode(self, mode: PrivacyMode) -> None:
        """Update active privacy mode and reconfigure client."""
        self._privacy_mode = mode
        self._init_client()

    def sanitize_payload(self, text: str) -> str:
        """Apply data minimization and redaction according to active privacy mode."""
        if self._privacy_mode == PrivacyMode.MODE_B_STATISTICAL:
            # Strip lines that contain textual names or values; keep strictly metric summaries
            sanitized_lines = []
            for line in text.splitlines():
                if any(
                    k in line.lower()
                    for k in [
                        "metric",
                        "confidence",
                        "severity",
                        "tier",
                        "count",
                        "score",
                        "variance",
                        "ratio",
                    ]
                ):
                    sanitized_lines.append(line)
            return "\n".join(sanitized_lines) if sanitized_lines else "Summary metrics only."

        if self._privacy_mode == PrivacyMode.MODE_C_REDACTED:
            sanitized = text
            for pattern, replacement in _REDACTION_PATTERNS:
                sanitized = pattern.sub(replacement, sanitized)
            return sanitized

        return text

    def generate_narrative(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate objective, grounded narrative text via Groq API.

        Implements LLMProviderProtocol. Returns empty string on failure or in Mode A,
        prompting NarrativeSynthesizer to use deterministic local templates.
        """
        if not self.is_available():
            return ""

        # 1. Enforce privacy redaction and compute payload hash
        sanitized_prompt = self.sanitize_payload(prompt)
        payload_hash = hashlib.sha256(sanitized_prompt.encode("utf-8")).hexdigest()

        sys_msg = (
            system_prompt
            or "You are an objective forensic document auditor. "
            "Explain the factual observations strictly based on the provided metrics. "
            "Do NOT draw legal conclusions of guilt or fraud. Keep response under 3 sentences."
        )

        start_time = time.time()
        try:
            assert self._client is not None

            # Execute Groq API chat completion
            chat_completion = self._client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": sanitized_prompt},
                ],
                model=self._model_name,
                temperature=0.1,  # Low temperature for deterministic, factual reporting
                max_tokens=256,
            )

            latency_ms = round((time.time() - start_time) * 1000, 2)
            response_text = ""
            if chat_completion.choices and len(chat_completion.choices) > 0:
                response_text = str(chat_completion.choices[0].message.content or "").strip()

            # Record audit trail entry
            if self._audit_logger is not None:
                self._audit_logger(
                    {
                        "timestamp": time.time(),
                        "provider": "Groq",
                        "model": self._model_name,
                        "privacy_mode": self._privacy_mode.value,
                        "payload_hash": payload_hash,
                        "latency_ms": latency_ms,
                        "tokens_used": getattr(chat_completion.usage, "total_tokens", 0)
                        if hasattr(chat_completion, "usage")
                        else 0,
                        "status": "SUCCESS",
                    }
                )

            return response_text

        except Exception as exc:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.warning(
                "Groq API narrative generation failed (%s); reverting to local template.", exc
            )

            if self._audit_logger is not None:
                self._audit_logger(
                    {
                        "timestamp": time.time(),
                        "provider": "Groq",
                        "model": self._model_name,
                        "privacy_mode": self._privacy_mode.value,
                        "payload_hash": payload_hash,
                        "latency_ms": latency_ms,
                        "status": f"FAILED: {exc}",
                    }
                )

            return ""
