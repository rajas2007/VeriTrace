"""Investigation Dashboard metrics and action banner widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from veritrace.gui.components.common import StatCard
from veritrace.gui.styles.tokens import ColorTokens, MetricTokens


class MetricCard(StatCard):
    """Visual metric card displaying an analytical counter and label (inherits StatCard)."""

    def __init__(
        self,
        label: str,
        value: str = "0",
        color: str = ColorTokens.ACCENT_PRIMARY,
        parent: Any = None,
    ) -> None:
        super().__init__(label=label, value=value, color=color, parent=parent)


class DashboardBannerWidget(QWidget):
    """Investigation header banner displaying metrics and correlation trigger controls."""

    run_correlation_requested = Signal(bool)  # is_order_closed
    run_forensics_requested = Signal()
    generate_dossier_requested = Signal()
    export_dossier_requested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # 1. Header Bar: Title & Subtitle (Left) + Finalized Switch & Primary CTA (Right)
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_lbl = QLabel("Forensic Intelligence Workstation", self)
        title_lbl.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_BASE}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
            f"color: {ColorTokens.TEXT_PRIMARY}; "
            "letter-spacing: -0.2px;"
        )
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Cross-document reconciliation, physical tamper detection & PS-2 legal audit dossiers",
            self,
        )
        sub_lbl.setStyleSheet(
            f"color: {ColorTokens.TEXT_MUTED}; font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        title_layout.addWidget(sub_lbl)
        header_bar.addLayout(title_layout, 1)

        self._chk_closed = QCheckBox("Orders Finalized", self)
        self._chk_closed.setToolTip(
            "When checked, under-deliveries are treated as shortages.\n"
            "When unchecked, partial deliveries on open orders are recognized without false alerts."
        )
        self._chk_closed.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_SM}; color: {ColorTokens.TEXT_SECONDARY};"
        )
        header_bar.addWidget(self._chk_closed)

        self._btn_correlate = QPushButton("⚡ Run Full Forensics", self)
        self._btn_correlate.setObjectName("primaryButton")
        self._btn_correlate.setStyleSheet(
            f"padding: 7px 16px; font-size: {MetricTokens.FONT_SIZE_SM}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD};"
        )
        self._btn_correlate.clicked.connect(self._on_correlate_clicked)
        header_bar.addWidget(self._btn_correlate)

        main_layout.addLayout(header_bar)

        # 2. Bottom Row: Stat Cards (Left) + Secondary Actions (Right)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(8)

        self._card_docs = MetricCard("DOCUMENTS", "0", ColorTokens.ACCENT_PRIMARY, self)
        bottom_row.addWidget(self._card_docs)

        self._card_findings = MetricCard("FINDINGS", "0", ColorTokens.TEXT_PRIMARY, self)
        bottom_row.addWidget(self._card_findings)

        self._card_critical = MetricCard("CRITICAL", "0", ColorTokens.SEVERITY_CRITICAL, self)
        bottom_row.addWidget(self._card_critical)

        self._card_high_med = MetricCard("HIGH / MED", "0", ColorTokens.SEVERITY_HIGH, self)
        bottom_row.addWidget(self._card_high_med)

        self._card_relations = MetricCard("RELATIONS", "0", ColorTokens.SEVERITY_LOW, self)
        bottom_row.addWidget(self._card_relations)

        bottom_row.addSpacing(10)

        self._btn_forensics = QPushButton("Scan Forensics", self)
        self._btn_forensics.setObjectName("secondaryButton")
        self._btn_forensics.setStyleSheet(
            f"padding: 6px 12px; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        self._btn_forensics.setToolTip(
            "Scan pages for visual forensics (signatures, morphology, pattern correspondences)"
        )
        self._btn_forensics.clicked.connect(self._on_forensics_clicked)
        bottom_row.addWidget(self._btn_forensics)

        self._btn_dossier = QPushButton("Compile PS-2 Dossier", self)
        self._btn_dossier.setObjectName("secondaryButton")
        self._btn_dossier.setStyleSheet(
            f"padding: 6px 12px; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        self._btn_dossier.setToolTip(
            "Compile complete 6-section PS-2 Investigation Dossier (JSON & ReportLab PDF)"
        )
        self._btn_dossier.clicked.connect(self._on_dossier_clicked)
        bottom_row.addWidget(self._btn_dossier)

        self._btn_export_dossier = QPushButton("Export PDF", self)
        self._btn_export_dossier.setObjectName("secondaryButton")
        self._btn_export_dossier.setStyleSheet(
            f"padding: 6px 12px; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
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
