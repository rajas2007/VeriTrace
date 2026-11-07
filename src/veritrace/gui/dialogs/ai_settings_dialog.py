"""Dialog for configuring AI reasoning, privacy modes, and API credentials."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from veritrace.application.services.investigation_service import InvestigationService
from veritrace.domain.enums.investigation import PrivacyMode

logger = logging.getLogger("veritrace.gui.ai_settings_dialog")


class AiSettingsDialog(QDialog):
    """User-accessible settings dialog for Grounded AI reasoning and privacy boundaries."""

    def __init__(
        self,
        investigation_service: InvestigationService,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Reasoning & Privacy Configuration")
        self.setMinimumWidth(520)
        self._service = investigation_service

        self._init_ui()
        self._load_current_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header_lbl = QLabel(
            "<b>Grounded AI Reasoning Configuration</b><br>"
            "<small>Configure cloud reasoning boundaries. VeriTrace operates in 100% offline "
            "Mode A by default. Automated finding creation or severity modification is "
            "strictly prohibited.</small>"
        )
        header_lbl.setWordWrap(True)
        layout.addWidget(header_lbl)

        group = QGroupBox("Privacy Governance & Credentials", self)
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._mode_combo = QComboBox(self)
        self._mode_combo.addItem(
            "Mode A: 100% Offline (Air-Gapped, Zero Data Egress)", PrivacyMode.MODE_A_OFFLINE
        )
        self._mode_combo.addItem(
            "Mode B: Statistical Only (Metrics only; zero text/PII)", PrivacyMode.MODE_B_STATISTICAL
        )
        self._mode_combo.addItem(
            "Mode C: Enterprise Redacted (PII regex masked)", PrivacyMode.MODE_C_REDACTED
        )
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("Privacy Mode:", self._mode_combo)

        key_layout = QHBoxLayout()
        self._api_key_edit = QLineEdit(self)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("gsk_...")
        key_layout.addWidget(self._api_key_edit)

        self._btn_test_conn = QPushButton("Probe API", self)
        self._btn_test_conn.setToolTip("Test connection and credential validity via minimal probe")
        self._btn_test_conn.clicked.connect(self._on_test_connection)
        key_layout.addWidget(self._btn_test_conn)

        form.addRow("Groq API Key:", key_layout)

        self._persist_checkbox = QCheckBox("Persist API key securely via Windows DPAPI", self)
        self._persist_checkbox.setChecked(True)
        form.addRow("", self._persist_checkbox)

        self._model_combo = QComboBox(self)
        self._model_combo.addItem("llama-3.3-70b-versatile")
        self._model_combo.addItem("llama-3.1-8b-instant")
        form.addRow("Model Engine:", self._model_combo)

        layout.addWidget(group)

        self._desc_lbl = QLabel(self)
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(self._desc_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_cancel = QPushButton("Cancel", self)
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_cancel)

        self._btn_save = QPushButton("Apply & Save", self)
        self._btn_save.setDefault(True)
        self._btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self._btn_save)

        layout.addLayout(btn_layout)

    def _load_current_settings(self) -> None:
        """Load current provider configuration and persisted credentials."""
        provider = self._service.get_llm_provider()
        if provider is not None and hasattr(provider, "get_privacy_mode"):
            mode = provider.get_privacy_mode()
            idx = self._mode_combo.findData(mode)
            if idx >= 0:
                self._mode_combo.setCurrentIndex(idx)
        else:
            self._mode_combo.setCurrentIndex(0)  # Default Mode A

        # Load persisted DPAPI key if available
        if hasattr(self._service, "get_persisted_ai_key"):
            persisted = self._service.get_persisted_ai_key()
            if isinstance(persisted, str) and persisted:
                self._api_key_edit.setText(persisted)
                self._persist_checkbox.setChecked(True)

        self._update_ui_state()

    def _on_mode_changed(self) -> None:
        self._update_ui_state()

    def _on_test_connection(self) -> None:
        """Execute non-destructive connection probe to verify credentials and connectivity."""
        key = self._api_key_edit.text().strip()
        model = self._model_combo.currentText()
        if not key:
            QMessageBox.warning(self, "API Key Missing", "Please enter a Groq API key to test.")
            return

        success, msg = self._service.test_ai_connection(api_key=key, model_name=model)
        if success:
            QMessageBox.information(self, "Connection Verified", msg)
        else:
            QMessageBox.critical(self, "Connection Failed", msg)

    def _update_ui_state(self) -> None:
        mode = self._mode_combo.currentData()
        if mode == PrivacyMode.MODE_A_OFFLINE:
            self._api_key_edit.setEnabled(False)
            self._api_key_edit.clear()
            self._btn_test_conn.setEnabled(False)
            self._persist_checkbox.setEnabled(False)
            self._desc_lbl.setText(
                "🔒 <b>Mode A Active:</b> Zero network or API requests. Offline local templates "
                "synthesize all dossier narratives. Complete air-gap guarantee."
            )
        elif mode == PrivacyMode.MODE_B_STATISTICAL:
            self._api_key_edit.setEnabled(True)
            self._btn_test_conn.setEnabled(True)
            self._persist_checkbox.setEnabled(True)
            self._desc_lbl.setText(
                "📊 <b>Mode B Active:</b> Only numerical metrics, severity tiers, and confidence "
                "ratios are transmitted. All names, company titles, and free-form text are "
                "stripped."
            )
        elif mode == PrivacyMode.MODE_C_REDACTED:
            self._api_key_edit.setEnabled(True)
            self._btn_test_conn.setEnabled(True)
            self._persist_checkbox.setEnabled(True)
            self._desc_lbl.setText(
                "🛡️ <b>Mode C Active:</b> Finding explanations are synthesized with automatic regex "
                "redaction for Indian financial numbers (PAN, GSTIN, Aadhaar, account numbers)."
            )

    def _on_save(self) -> None:
        """Apply configured provider to investigation service."""
        mode = self._mode_combo.currentData()
        api_key = self._api_key_edit.text().strip() or None
        model_name = self._model_combo.currentText()
        persist_key = (
            self._persist_checkbox.isChecked() if mode != PrivacyMode.MODE_A_OFFLINE else False
        )

        if mode != PrivacyMode.MODE_A_OFFLINE and not api_key:
            mode_str = getattr(mode, "value", str(mode))
            QMessageBox.warning(
                self,
                "API Key Required",
                f"Privacy {mode_str} requires a valid Groq API key to activate.",
            )
            return

        if mode == PrivacyMode.MODE_C_REDACTED:
            reply = QMessageBox.question(
                self,
                "Explicit Cloud Authorization",
                "Mode C transmits regex-redacted document finding summaries to the external "
                "Groq cloud endpoint.\n\n"
                "Note: Regex patterns redact canonical PAN, GSTIN, Aadhaar, and account numbers, "
                "but cannot guarantee complete omission of non-standard names or descriptions.\n\n"
                "Do you explicitly authorize external transmission under Mode C?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._service.configure_ai_provider(
            privacy_mode=mode,
            api_key=api_key,
            model_name=model_name,
            persist_key=persist_key,
        )
        mode_str = getattr(mode, "value", str(mode))
        logger.info("AI reasoning configured in %s.", mode_str)
        self.accept()
