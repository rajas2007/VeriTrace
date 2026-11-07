"""Unit tests for AI Reasoning & Privacy Settings Dialog."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from veritrace.application.services.investigation_service import InvestigationService
from veritrace.gui.dialogs.ai_settings_dialog import AiSettingsDialog
from veritrace.infrastructure.ai.groq_client import GroqLLMProvider, PrivacyMode


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_ai_settings_dialog_default_mode_a(qapp):
    """Verify dialog opens in Mode A by default with disabled API key edit."""
    mock_service = MagicMock(spec=InvestigationService)
    mock_service.get_llm_provider.return_value = None

    dialog = AiSettingsDialog(mock_service)
    assert dialog._mode_combo.currentData() == PrivacyMode.MODE_A_OFFLINE
    assert dialog._api_key_edit.isEnabled() is False


def test_ai_settings_dialog_mode_b_enables_key(qapp):
    """Verify selecting Mode B enables API key edit."""
    mock_service = MagicMock(spec=InvestigationService)
    mock_service.get_llm_provider.return_value = None

    dialog = AiSettingsDialog(mock_service)
    dialog._mode_combo.setCurrentIndex(1)  # Mode B

    assert dialog._mode_combo.currentData() == PrivacyMode.MODE_B_STATISTICAL
    assert dialog._api_key_edit.isEnabled() is True


def test_ai_settings_dialog_save_mode_c_configures_service(qapp, monkeypatch):
    """Verify saving with Mode C and key configures GroqLLMProvider on service when authorized."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        "veritrace.gui.dialogs.ai_settings_dialog.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    mock_service = MagicMock(spec=InvestigationService)
    mock_service.get_llm_provider.return_value = None

    dialog = AiSettingsDialog(mock_service)
    dialog._mode_combo.setCurrentIndex(2)  # Mode C
    dialog._api_key_edit.setText("test_valid_key_12345")

    dialog._on_save()

    mock_service.configure_ai_provider.assert_called_once_with(
        privacy_mode=PrivacyMode.MODE_C_REDACTED,
        api_key="test_valid_key_12345",
        model_name="llama-3.3-70b-versatile",
        persist_key=True,
    )


def test_ai_settings_dialog_mode_c_refused_without_authorization(qapp, monkeypatch):
    """Verify Mode C is aborted if user denies explicit cloud transmission authorization."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        "veritrace.gui.dialogs.ai_settings_dialog.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )
    mock_service = MagicMock(spec=InvestigationService)
    mock_service.get_llm_provider.return_value = None

    dialog = AiSettingsDialog(mock_service)
    dialog._mode_combo.setCurrentIndex(2)  # Mode C
    dialog._api_key_edit.setText("test_valid_key_12345")

    dialog._on_save()

    # Service should NOT be configured if explicit authorization is denied
    mock_service.configure_ai_provider.assert_not_called()


def test_ai_settings_dialog_save_mode_a_clears_key(qapp):
    """Verify selecting Mode A configures offline provider."""
    mock_service = MagicMock(spec=InvestigationService)
    existing_provider = GroqLLMProvider(privacy_mode=PrivacyMode.MODE_C_REDACTED)
    mock_service.get_llm_provider.return_value = existing_provider

    dialog = AiSettingsDialog(mock_service)
    dialog._mode_combo.setCurrentIndex(0)  # Mode A

    dialog._on_save()

    mock_service.configure_ai_provider.assert_called_once_with(
        privacy_mode=PrivacyMode.MODE_A_OFFLINE,
        api_key=None,
        model_name="llama-3.3-70b-versatile",
        persist_key=False,
    )


def test_ai_settings_dialog_test_connection_trigger(qapp, monkeypatch):
    """Verify probe API button triggers service test connection."""
    q_target = "veritrace.gui.dialogs.ai_settings_dialog.QMessageBox.information"
    monkeypatch.setattr(q_target, MagicMock())
    mock_service = MagicMock(spec=InvestigationService)
    mock_service.get_llm_provider.return_value = None
    mock_service.test_ai_connection.return_value = (True, "Connection verified successfully.")

    dialog = AiSettingsDialog(mock_service)
    dialog._mode_combo.setCurrentIndex(1)  # Mode B
    dialog._api_key_edit.setText("test_probe_key")

    dialog._on_test_connection()
    mock_service.test_ai_connection.assert_called_once_with(
        api_key="test_probe_key", model_name="llama-3.3-70b-versatile"
    )


def test_ai_settings_dialog_real_service_integration(qapp, monkeypatch):
    """Verify end-to-end wiring with real InvestigationService instance."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        "veritrace.gui.dialogs.ai_settings_dialog.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    real_service = InvestigationService(uow_factory=lambda: None)

    dialog = AiSettingsDialog(real_service)
    dialog._mode_combo.setCurrentIndex(2)  # Mode C
    dialog._api_key_edit.setText("test_real_key")
    dialog._on_save()

    provider = real_service.get_llm_provider()
    assert isinstance(provider, GroqLLMProvider)
    assert provider.get_privacy_mode() == PrivacyMode.MODE_C_REDACTED
