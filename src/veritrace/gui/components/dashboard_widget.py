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
        self, label: str, value: str = "0", color: str = "#38bdf8", parent: Any = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(80)
        self.setStyleSheet(
            f"QFrame#card {{ background-color: #0f1420; border: 1px solid #1c2438; "
            f"border-top: 3px solid {color}; border-radius: 6px; }}"
            f"QFrame#card:hover {{ border-color: {color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        self._lbl_value = QLabel(value, self)
        self._lbl_value.setStyleSheet(
            f"font-size: 19px; font-weight: 800; color: {color}; "
            f"font-family: 'Segoe UI', monospace;"
        )
        self._lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_value)

        self._lbl_label = QLabel(label, self)
        self._lbl_label.setStyleSheet(
            "color: #94a3b8; font-size: 9.5px; font-weight: 700; letter-spacing: 0.6px;"
        )
        self._lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_label)

    def set_value(self, value: str | int) -> None:
        """Update counter value."""
        self._lbl_value.setText(str(value))


class DashboardBannerWidget(QWidget):
    """Investigation header banner displaying metrics and correlation trigger controls."""

    run_correlation_requested = Signal(bool)  # is_order_closed
    run_forensics_requested = Signal()
    generate_dossier_requested = Signal()
    export_dossier_requested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 4)
        main_layout.setSpacing(6)

        # 1. Header Bar: Title (Left) + Order Status & Primary Run Trigger (Right)
        header_bar = QHBoxLayout()
        header_bar.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        title_lbl = QLabel("Cross-Document Forensic Intelligence Command", self)
        title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 800; color: #f1f5f9; letter-spacing: 0.4px;"
        )
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Deterministic cross-document alignment, physical consistency & PS-2 dossiers",
            self,
        )
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_layout.addWidget(sub_lbl)
        header_bar.addLayout(title_layout, 1)

        self._chk_closed = QCheckBox("Orders Finalized", self)
        self._chk_closed.setToolTip(
            "When checked, under-deliveries are treated as shortages. "
            "When unchecked, partial deliveries on open orders are recognized without false alerts."
        )
        header_bar.addWidget(self._chk_closed)

        self._btn_correlate = QPushButton("⚡ Run Full Forensics", self)
        self._btn_correlate.setObjectName("primaryButton")
        self._btn_correlate.setStyleSheet("padding: 6px 14px; font-size: 12px; font-weight: 700;")
        self._btn_correlate.clicked.connect(self._on_correlate_clicked)
        header_bar.addWidget(self._btn_correlate)

        main_layout.addLayout(header_bar)

        # 2. Bottom Row: Metric Cards (Left) + Secondary Action Buttons (Right)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self._card_docs = MetricCard("DOCUMENTS", "0", "#38bdf8", self)
        bottom_row.addWidget(self._card_docs)

        self._card_findings = MetricCard("FINDINGS", "0", "#f1f5f9", self)
        bottom_row.addWidget(self._card_findings)

        self._card_critical = MetricCard("CRITICAL", "0", "#ef4444", self)
        bottom_row.addWidget(self._card_critical)

        self._card_high_med = MetricCard("HIGH / MED", "0", "#f97316", self)
        bottom_row.addWidget(self._card_high_med)

        self._card_relations = MetricCard("RELATIONS", "0", "#10b981", self)
        bottom_row.addWidget(self._card_relations)

        bottom_row.addSpacing(6)

        self._btn_forensics = QPushButton("Scan Forensics", self)
        self._btn_forensics.setStyleSheet("padding: 6px 12px; font-size: 11px; font-weight: 600;")
        self._btn_forensics.setToolTip(
            "Scan pages for visual forensics (signatures, morphology, pattern correspondences)"
        )
        self._btn_forensics.clicked.connect(self._on_forensics_clicked)
        bottom_row.addWidget(self._btn_forensics)

        self._btn_dossier = QPushButton("Compile PS-2 Dossier", self)
        self._btn_dossier.setStyleSheet("padding: 6px 12px; font-size: 11px; font-weight: 600;")
        self._btn_dossier.setToolTip(
            "Compile complete 6-section PS-2 Investigation Dossier (JSON & ReportLab PDF)"
        )
        self._btn_dossier.clicked.connect(self._on_dossier_clicked)
        bottom_row.addWidget(self._btn_dossier)

        self._btn_export_dossier = QPushButton("📄 Export PDF", self)
        self._btn_export_dossier.setObjectName("accentButton")
        self._btn_export_dossier.setStyleSheet(
            "padding: 6px 12px; font-size: 11px; font-weight: 700;"
        )
        self._btn_export_dossier.setToolTip("Export sealed legal PS-2 Investigation Dossier PDF")
        self._btn_export_dossier.clicked.connect(self.export_dossier_requested.emit)
        bottom_row.addWidget(self._btn_export_dossier)

        main_layout.addLayout(bottom_row)

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
