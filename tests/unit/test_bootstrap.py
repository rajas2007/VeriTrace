"""Unit tests for VeriTrace desktop application bootstrap and directory resolution."""

import os
from pathlib import Path

from veritrace.bootstrap import (
    bootstrap_application,
    resolve_data_directory,
    setup_logging,
)


def test_resolve_data_directory_custom_env(monkeypatch):
    """Verify that VERITRACE_DATA_DIR environment variable is respected."""
    custom_path = "C:\\CustomVeriTraceData" if os.name == "nt" else "/tmp/custom_veritrace"
    monkeypatch.setenv("VERITRACE_DATA_DIR", custom_path)
    resolved = resolve_data_directory()
    assert resolved == Path(custom_path)


def test_resolve_data_directory_default(monkeypatch):
    """Verify default data directory resolution when environment variable is unset."""
    monkeypatch.delenv("VERITRACE_DATA_DIR", raising=False)
    resolved = resolve_data_directory()
    assert "VeriTrace" in str(resolved) or ".veritrace" in str(resolved)


def test_setup_logging_idempotent():
    """Verify logging setup executes without raising exceptions."""
    setup_logging()


def test_bootstrap_application(monkeypatch):
    """Verify bootstrap initialization runs cleanly."""
    monkeypatch.delenv("VERITRACE_DATA_DIR", raising=False)
    bootstrap_application()
