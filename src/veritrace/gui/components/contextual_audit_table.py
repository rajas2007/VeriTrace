"""Contextual Procurement Arithmetic and Chronology Audit Component."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.forensics import ContextualAuditItemDTO
from veritrace.gui.styles.tokens import ColorTokens, MetricTokens


class ContextualAuditWidget(QWidget):
    """Forensic workbench for contextual procurement math, weighbridge, and chronology audits."""

    run_audit_requested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_lbl = QLabel("Contextual Procurement & Chronology Audit", self)
        title_lbl.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_BASE}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
            f"color: {ColorTokens.TEXT_PRIMARY};"
        )
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Procurement arithmetic, weighbridge reconciliation, and temporal audit",
            self,
        )
        sub_lbl.setStyleSheet(
            f"color: {ColorTokens.TEXT_MUTED}; font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        title_layout.addWidget(sub_lbl)
        header_bar.addLayout(title_layout, 1)

        self._btn_audit = QPushButton("⚡ Run Contextual Audit", self)
        self._btn_audit.setObjectName("primaryButton")
        self._btn_audit.setStyleSheet(
            f"padding: 7px 16px; font-size: {MetricTokens.FONT_SIZE_SM}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD};"
        )
        self._btn_audit.clicked.connect(self.run_audit_requested.emit)
        header_bar.addWidget(self._btn_audit)

        main_layout.addLayout(header_bar)

        # Splitter: Table above, detail card below
        splitter = QSplitter(Qt.Orientation.Vertical, self)

        # Top Table
        self._table = QTableWidget(splitter)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Rule Code", "Category", "Status", "Expected Value", "Actual Value", "Involved Docs"]
        )
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self._table)

        # Bottom Detail Card
        bottom_container = QWidget(splitter)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        detail_card = QFrame(bottom_container)
        detail_card.setObjectName("card")
        detail_card.setStyleSheet(
            f"background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_MD}; "
            "padding: 6px;"
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(10, 10, 10, 10)
        detail_layout.setSpacing(6)

        self._lbl_detail_title = QLabel(
            "Select an audit item above to view forensic details", detail_card
        )
        self._lbl_detail_title.setStyleSheet(
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
            f"font-size: {MetricTokens.FONT_SIZE_BASE}; "
            f"color: {ColorTokens.TEXT_PRIMARY};"
        )
        detail_layout.addWidget(self._lbl_detail_title)

        self._lbl_detail_badge = QLabel("", detail_card)
        detail_layout.addWidget(self._lbl_detail_badge)

        self._txt_detail_desc = QTextEdit(detail_card)
        self._txt_detail_desc.setReadOnly(True)
        self._txt_detail_desc.setMaximumHeight(70)
        detail_layout.addWidget(self._txt_detail_desc)

        bottom_layout.addWidget(detail_card)
        splitter.addWidget(bottom_container)
        splitter.setSizes([260, 130])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

        self._items: list[ContextualAuditItemDTO] = []

    def set_audit_items(self, items: list[ContextualAuditItemDTO]) -> None:
        """Populate table with contextual audit items."""
        self._items = items
        self._table.setRowCount(len(items))

        bold_font = QFont(MetricTokens.FONT_FAMILY_SANS, 9, QFont.Weight.DemiBold)
        mono_font = QFont(MetricTokens.FONT_FAMILY_MONO, 9, QFont.Weight.Normal)

        for row, item in enumerate(items):
            code_item = QTableWidgetItem(item.rule_code)
            code_item.setFont(mono_font)
            self._table.setItem(row, 0, code_item)

            self._table.setItem(row, 1, QTableWidgetItem(item.category.replace("_", " ")))

            status_display = f"● {item.status}"
            status_item = QTableWidgetItem(status_display)
            status_item.setFont(bold_font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if item.status == "PASSED":
                status_item.setForeground(QColor(ColorTokens.SEVERITY_LOW))
            else:
                status_item.setForeground(QColor(ColorTokens.SEVERITY_CRITICAL))
            self._table.setItem(row, 2, status_item)

            self._table.setItem(row, 3, QTableWidgetItem(item.expected_value))
            self._table.setItem(row, 4, QTableWidgetItem(item.actual_value))
            self._table.setItem(row, 5, QTableWidgetItem(", ".join(item.involved_documents)))

        if items:
            self._table.selectRow(0)

    def _on_row_selected(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self._items):
            return

        item = self._items[row]
        self._lbl_detail_title.setText(f"{item.rule_code}: {item.rule_name}")

        color = (
            ColorTokens.SEVERITY_LOW if item.status == "PASSED" else ColorTokens.SEVERITY_CRITICAL
        )
        self._lbl_detail_badge.setText(
            f"Category: <b>{item.category}</b>  |  "
            f"Status: <b style='color:{color};'>{item.status}</b>  |  "
            f"Severity: <b>{item.severity}</b>"
        )
        self._txt_detail_desc.setPlainText(
            f"{item.description}\n\n"
            f"Expected: {item.expected_value}\n"
            f"Observed: {item.actual_value}\n"
        )
