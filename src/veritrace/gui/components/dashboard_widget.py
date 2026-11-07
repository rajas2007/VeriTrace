"""Investigation Dashboard metrics and action banner widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MetricCard(QFrame):
    """Visual metric card displaying an analytical counter and label."""

    def __init__(
        self, label: str, value: str = "0", color: str = "#58a6ff", parent: Any = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._lbl_value = QLabel(value, self)
        self._lbl_value.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        self._lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_value)

        self._lbl_label = QLabel(label, self)
        self._lbl_label.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )
        self._lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_label)

    def set_value(self, value: str | int) -> None:
        """Update counter value."""
        self._lbl_value.setText(str(value))


class DashboardBannerWidget(QWidget):
    """Investigation header banner displaying metrics and correlation trigger controls."""

    run_correlation_requested = Signal(bool)  # is_order_closed
<<<<<<< HEAD
    run_forensics_requested = Signal()
    generate_dossier_requested = Signal()
=======
    export_dossier_requested = Signal()
>>>>>>> 4b23890e073b4435bd8606178ff05403f236f444

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 6)
        main_layout.setSpacing(8)

        # 1. Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        title_layout = QVBoxLayout()
        title_lbl = QLabel("Cross-Document Intelligence & Forensic Command Center", self)
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #ffffff; letter-spacing: 0.5px;"
        )
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Deterministic cross-document alignment, physical consistency, and PS-2 dossiers",
            self,
        )
        sub_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        title_layout.addWidget(sub_lbl)
        action_bar.addLayout(title_layout, 1)

        self._chk_closed = QCheckBox("Orders Finalized / Closed", self)
        self._chk_closed.setToolTip(
            "When checked, under-deliveries are treated as shortages. "
            "When unchecked, partial deliveries on open orders are recognized without false alerts."
        )
        action_bar.addWidget(self._chk_closed)

        self._btn_correlate = QPushButton("⚡ Run Full Forensics", self)
        self._btn_correlate.setObjectName("primaryButton")
        self._btn_correlate.setStyleSheet("padding: 8px 16px; font-size: 13px;")
        self._btn_correlate.clicked.connect(self._on_correlate_clicked)
        action_bar.addWidget(self._btn_correlate)

<<<<<<< HEAD
        self._btn_forensics = QPushButton("Scan Forensics", self)
        self._btn_forensics.setStyleSheet("padding: 8px 16px; font-size: 13px; font-weight: 600;")
        self._btn_forensics.setToolTip(
            "Scan pages for visual forensics (signatures, morphology, pattern correspondences)"
        )
        self._btn_forensics.clicked.connect(self._on_forensics_clicked)
        action_bar.addWidget(self._btn_forensics)

        self._btn_dossier = QPushButton("Compile PS-2 Dossier", self)
        self._btn_dossier.setStyleSheet("padding: 8px 16px; font-size: 13px; font-weight: 600;")
        self._btn_dossier.setToolTip(
            "Compile complete 6-section PS-2 Investigation Dossier (JSON & ReportLab PDF)"
        )
        self._btn_dossier.clicked.connect(self._on_dossier_clicked)
        action_bar.addWidget(self._btn_dossier)
=======
        self._btn_export_dossier = QPushButton("📄 Export PS-2 Dossier (PDF)", self)
        self._btn_export_dossier.setObjectName("accentButton")
        self._btn_export_dossier.setStyleSheet("padding: 8px 16px; font-size: 13px;")
        self._btn_export_dossier.clicked.connect(self.export_dossier_requested.emit)
        action_bar.addWidget(self._btn_export_dossier)
>>>>>>> 4b23890e073b4435bd8606178ff05403f236f444

        main_layout.addLayout(action_bar)

        # 2. Metric Cards Row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(8)

        self._card_docs = MetricCard("DOCUMENTS", "0", "#58a6ff", self)
        cards_layout.addWidget(self._card_docs)

        self._card_findings = MetricCard("FINDINGS", "0", "#f0f6fc", self)
        cards_layout.addWidget(self._card_findings)

        self._card_critical = MetricCard("CRITICAL", "0", "#f85149", self)
        cards_layout.addWidget(self._card_critical)

        self._card_high_med = MetricCard("HIGH / MEDIUM", "0", "#f0883e", self)
        cards_layout.addWidget(self._card_high_med)

        self._card_relations = MetricCard("RELATIONS", "0", "#3fb950", self)
        cards_layout.addWidget(self._card_relations)

        main_layout.addLayout(cards_layout)

    def set_metrics(
        self,
        docs_count: int,
        findings_count: int,
        critical_count: int,
        high_med_count: int,
        relations_count: int,
    ) -> None:
        """Update metrics card counters."""
        self._card_docs.set_value(docs_count)
        self._card_findings.set_value(findings_count)
        self._card_critical.set_value(critical_count)
        self._card_high_med.set_value(high_med_count)
        self._card_relations.set_value(relations_count)

    def set_correlate_enabled(self, enabled: bool) -> None:
        """Enable or disable correlation action button."""
        self._btn_correlate.setEnabled(enabled)

    def set_forensics_enabled(self, enabled: bool) -> None:
        """Enable or disable visual forensics action button."""
        self._btn_forensics.setEnabled(enabled)

    def set_dossier_enabled(self, enabled: bool) -> None:
        """Enable or disable dossier compilation action button."""
        self._btn_dossier.setEnabled(enabled)

    def _on_correlate_clicked(self) -> None:
        is_closed = self._chk_closed.isChecked()
        self.run_correlation_requested.emit(is_closed)

    def _on_forensics_clicked(self) -> None:
        self.run_forensics_requested.emit()

    def _on_dossier_clicked(self) -> None:
        self.generate_dossier_requested.emit()
