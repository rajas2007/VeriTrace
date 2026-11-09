"""Contradiction Matrix table component displaying cross-document discrepancies."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.investigation import FindingResponseDTO
from veritrace.gui.components.common import EmptyStateWidget
from veritrace.gui.styles.theme_manager import ThemeManager
from veritrace.gui.styles.tokens import ColorTokens, MetricTokens


class FindingTableWidget(QWidget):
    """Contradiction Matrix table displaying detected inconsistencies and anomalies."""

    finding_selected = Signal(str)  # finding_id
    finding_activated = Signal(str)  # finding_id
    run_forensics_requested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._all_findings: list[FindingResponseDTO] = []
        self._filtered_findings: list[FindingResponseDTO] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 1. Filter Bar
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        self._search_input = QLineEdit(self)
        self._search_input.setPlaceholderText("Search discrepancy title or narrative...")
        self._search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._search_input, 1)

        self._filter_severity = QComboBox(self)
        self._filter_severity.addItems(["All Severities", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
        self._filter_severity.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._filter_severity)

        self._filter_status = QComboBox(self)
        self._filter_status.addItems(
            [
                "All Review Statuses",
                "PENDING_REVIEW",
                "CONFIRMED",
                "DISMISSED",
                "ANNOTATED",
            ]
        )
        self._filter_status.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._filter_status)

        self._count_label = QLabel("0 findings", self)
        self._count_label.setStyleSheet(
            f"color: {ColorTokens.TEXT_MUTED}; "
            f"font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM}; "
            "padding: 4px 8px;"
        )
        filter_layout.addWidget(self._count_label)

        layout.addLayout(filter_layout)

        # 2. Main Area: Stacked Table & Empty State
        self._stack = QStackedWidget(self)

        # Empty State
        self._empty_state = EmptyStateWidget(
            headline="No Contradictions Detected",
            description=(
                "Ingest case documents and run cross-document correlation to scan discrepancies."
            ),
            icon_char="🔍",
            cta_text="⚡ Run Full Forensics",
            parent=self._stack,
        )
        self._empty_state.cta_clicked.connect(self.run_forensics_requested.emit)
        self._stack.addWidget(self._empty_state)

        # Table
        self._table = QTableWidget(self._stack)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            [
                "Severity",
                "Epistemic Tier",
                "Category",
                "Discrepancy / Title",
                "Confidence",
                "Review Status",
            ]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(self._on_double_clicked)
        self._stack.addWidget(self._table)

        layout.addWidget(self._stack, 1)

    def set_findings(self, findings: list[FindingResponseDTO]) -> None:
        """Update findings data and refresh filtered view."""
        self._all_findings = findings
        self._apply_filters()

    def _apply_filters(self) -> None:
        sev_filter = self._filter_severity.currentText()
        stat_filter = self._filter_status.currentText()
        query = self._search_input.text().strip().lower()

        filtered: list[FindingResponseDTO] = []
        for f in self._all_findings:
            if sev_filter != "All Severities" and f.severity.value != sev_filter:
                continue
            if stat_filter != "All Review Statuses" and f.review_status.value != stat_filter:
                continue
            if (
                query
                and query not in f.title.lower()
                and query not in f.narrative_explanation.lower()
            ):
                continue
            filtered.append(f)

        self._filtered_findings = filtered

        if not self._all_findings:
            self._count_label.setText("0 findings")
            self._stack.setCurrentIndex(0)  # Show empty state
        else:
            self._count_label.setText(f"{len(filtered)} of {len(self._all_findings)} findings")
            self._stack.setCurrentIndex(1)  # Show table

        self._populate_table()

    def _populate_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(len(self._filtered_findings))

        bold_font = QFont(MetricTokens.FONT_FAMILY_SANS, 9, QFont.Weight.DemiBold)
        mono_font = QFont(MetricTokens.FONT_FAMILY_MONO, 9, QFont.Weight.Normal)

        for row, f in enumerate(self._filtered_findings):
            # 0: Severity
            item_sev = QTableWidgetItem(f"● {f.severity.value}")
            item_sev.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sev_color = QColor(ThemeManager.get_severity_color(f.severity.value))
            item_sev.setForeground(sev_color)
            item_sev.setFont(bold_font)
            item_sev.setData(Qt.ItemDataRole.UserRole, f.id)
            self._table.setItem(row, 0, item_sev)

            # 1: Epistemic Tier
            tier_display = f.epistemic_tier.value.replace("_", " ")
            item_tier = QTableWidgetItem(tier_display)
            tier_color = QColor(ThemeManager.get_tier_color(f.epistemic_tier.value))
            item_tier.setForeground(tier_color)
            item_tier.setFont(bold_font)
            item_tier.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, item_tier)

            # 2: Category
            cat_display = f.category.value.replace("_", " ")
            item_cat = QTableWidgetItem(cat_display)
            item_cat.setFont(mono_font)
            self._table.setItem(row, 2, item_cat)

            # 3: Title
            item_title = QTableWidgetItem(f.title)
            item_title.setToolTip(f.narrative_explanation)
            self._table.setItem(row, 3, item_title)

            # 4: Confidence
            item_conf = QTableWidgetItem(f"{f.confidence * 100:.0f}%")
            item_conf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_conf.setFont(mono_font)
            self._table.setItem(row, 4, item_conf)

            # 5: Review Status
            status_display = f.review_status.value.replace("_", " ")
            item_status = QTableWidgetItem(status_display)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_color = QColor(ThemeManager.get_status_color(f.review_status.value))
            item_status.setForeground(status_color)
            item_status.setFont(bold_font)
            self._table.setItem(row, 5, item_status)

        self._table.blockSignals(False)

        # Retain selection if valid
        if self._filtered_findings:
            self._table.selectRow(0)

    def _on_selection_changed(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if 0 <= row < len(self._filtered_findings):
                finding_id = self._filtered_findings[row].id
                self.finding_selected.emit(finding_id)

    def _on_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if 0 <= row < len(self._filtered_findings):
            finding_id = self._filtered_findings[row].id
            self.finding_activated.emit(finding_id)

    def select_finding_by_id(self, finding_id: str) -> None:
        """Select row matching the specified finding ID."""
        for row, f in enumerate(self._filtered_findings):
            if f.id == finding_id:
                self._table.selectRow(row)
                break
