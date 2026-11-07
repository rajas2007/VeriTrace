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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.investigation import FindingResponseDTO
from veritrace.gui.styles.theme_manager import ThemeManager


class FindingTableWidget(QWidget):
    """Contradiction Matrix table displaying detected inconsistencies and anomalies."""

    finding_selected = Signal(str)  # finding_id
    finding_activated = Signal(str)  # finding_id

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._all_findings: list[FindingResponseDTO] = []
        self._filtered_findings: list[FindingResponseDTO] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        lbl_filter = QLabel("🔍 Filter:", self)
        lbl_filter.setStyleSheet(
            "color: #38bdf8; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;"
        )
        filter_layout.addWidget(lbl_filter)

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

        self._search_input = QLineEdit(self)
        self._search_input.setPlaceholderText("Search discrepancy title or narrative...")
        self._search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._search_input, 1)

        self._count_label = QLabel("0 findings", self)
        self._count_label.setStyleSheet(
            "color: #94a3b8; font-weight: 600; font-size: 11px; "
            "background: #0f1420; border: 1px solid #1c2438; border-radius: 6px; padding: 5px 10px;"
        )
        filter_layout.addWidget(self._count_label)

        layout.addLayout(filter_layout)

        # Table
        self._table = QTableWidget(self)
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

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self._table, 1)

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
        if self._all_findings:
            self._count_label.setText(f"{len(filtered)} of {len(self._all_findings)} findings")
        else:
            self._count_label.setText(
                "0 findings — Click '⚡ Run Full Forensics' to analyze"
            )
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(len(self._filtered_findings))

        bold_font = QFont("Segoe UI", 9, QFont.Weight.Bold)

        for row, f in enumerate(self._filtered_findings):
            # 0: Severity
            item_sev = QTableWidgetItem(f.severity.value)
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
            self._table.setItem(row, 1, item_tier)

            # 2: Category
            cat_display = f.category.value.replace("_", " ")
            item_cat = QTableWidgetItem(cat_display)
            self._table.setItem(row, 2, item_cat)

            # 3: Title
            item_title = QTableWidgetItem(f.title)
            item_title.setToolTip(f.narrative_explanation)
            self._table.setItem(row, 3, item_title)

            # 4: Confidence
            item_conf = QTableWidgetItem(f"{f.confidence * 100:.0f}%")
            item_conf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_conf.setFont(bold_font)
            self._table.setItem(row, 4, item_conf)

            # 5: Review Status
            item_status = QTableWidgetItem(f.review_status.value)
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
