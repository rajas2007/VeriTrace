"""Signature Forensics Workbench component."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.forensics import SignatureComparisonDTO


class SignatureWorkbenchWidget(QWidget):
    """Forensic workbench for signature detection, Hu moment analysis, and ASTM verification."""

    run_verification_requested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(8)

        title_layout = QVBoxLayout()
        title_lbl = QLabel("✍️ Signature Forensics & Hu Moment Verification", self)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "ASTM E3079 6-Level Scale, Invariant Hu Moments, and Optical Stroke Analysis",
            self,
        )
        sub_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        title_layout.addWidget(sub_lbl)
        header_bar.addLayout(title_layout, 1)

        self._btn_verify = QPushButton("Run Signature Verification", self)
        self._btn_verify.setObjectName("primaryButton")
        self._btn_verify.clicked.connect(self.run_verification_requested.emit)
        header_bar.addWidget(self._btn_verify)

        main_layout.addLayout(header_bar)

        # Splitter: Left Table / Right Side-by-Side Comparison
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Table of signature comparisons
        left_box = QWidget(splitter)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        lbl_table_hdr = QLabel("DETECTED QUESTIONED SIGNATURES", left_box)
        lbl_table_hdr.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 11px;")
        left_layout.addWidget(lbl_table_hdr)

        self._table = QTableWidget(left_box)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Questioned Doc", "Reference Doc", "Hu Distance", "Verdict"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        left_layout.addWidget(self._table, 1)
        splitter.addWidget(left_box)

        # Right Inspection Box
        right_box = QWidget(splitter)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Crops card
        crops_card = QFrame(right_box)
        crops_card.setObjectName("card")
        crops_layout = QVBoxLayout(crops_card)
        crops_layout.setContentsMargins(10, 10, 10, 10)
        crops_layout.setSpacing(8)

        lbl_preview_hdr = QLabel("OPTICAL STROKE COMPARISON", crops_card)
        lbl_preview_hdr.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        crops_layout.addWidget(lbl_preview_hdr)

        crops_row = QHBoxLayout()
        crops_row.setSpacing(12)

        # Questioned preview
        q_layout = QVBoxLayout()
        self._lbl_q_title = QLabel("Questioned Signature", crops_card)
        self._lbl_q_title.setStyleSheet("font-weight: 600; color: #f0f6fc; font-size: 11px;")
        q_layout.addWidget(self._lbl_q_title)
        self._lbl_q_img = QLabel("No Image", crops_card)
        self._lbl_q_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_q_img.setMinimumSize(180, 110)
        self._lbl_q_img.setStyleSheet(
            "background: #090d16; border: 1px dashed #30363d; border-radius: 4px;"
        )
        q_layout.addWidget(self._lbl_q_img)
        crops_row.addLayout(q_layout)

        # Reference preview
        r_layout = QVBoxLayout()
        self._lbl_r_title = QLabel("Reference Enrolled", crops_card)
        self._lbl_r_title.setStyleSheet("font-weight: 600; color: #f0f6fc; font-size: 11px;")
        r_layout.addWidget(self._lbl_r_title)
        self._lbl_r_img = QLabel("No Image", crops_card)
        self._lbl_r_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_r_img.setMinimumSize(180, 110)
        self._lbl_r_img.setStyleSheet(
            "background: #090d16; border: 1px dashed #30363d; border-radius: 4px;"
        )
        r_layout.addWidget(self._lbl_r_img)
        crops_row.addLayout(r_layout)

        crops_layout.addLayout(crops_row)
        right_layout.addWidget(crops_card)

        # Metrics Card
        metrics_card = QFrame(right_box)
        metrics_card.setObjectName("card")
        metrics_layout = QVBoxLayout(metrics_card)
        metrics_layout.setContentsMargins(10, 10, 10, 10)
        metrics_layout.setSpacing(6)

        lbl_metric_hdr = QLabel("ASTM E3079 VERIFICATION METRICS", metrics_card)
        lbl_metric_hdr.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 11px;")
        metrics_layout.addWidget(lbl_metric_hdr)

        self._lbl_verdict_badge = QLabel("SELECT A COMPARISON ROW", metrics_card)
        self._lbl_verdict_badge.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #58a6ff; padding: 4px 8px; "
            "background: #161b22; border: 1px solid #30363d; border-radius: 4px;"
        )
        metrics_layout.addWidget(self._lbl_verdict_badge)

        self._lbl_hu_distance = QLabel("Hu Invariant Moments Distance: —", metrics_card)
        self._lbl_hu_distance.setStyleSheet("color: #f0f6fc; font-size: 12px;")
        metrics_layout.addWidget(self._lbl_hu_distance)

        self._bar_distance = QProgressBar(metrics_card)
        self._bar_distance.setRange(0, 100)
        self._bar_distance.setValue(0)
        self._bar_distance.setFixedHeight(8)
        self._bar_distance.setTextVisible(False)
        metrics_layout.addWidget(self._bar_distance)

        self._lbl_stroke_density = QLabel("Stroke Density Ratio: —", metrics_card)
        self._lbl_stroke_density.setStyleSheet("color: #8b949e; font-size: 11px;")
        metrics_layout.addWidget(self._lbl_stroke_density)

        self._txt_explanation = QTextEdit(metrics_card)
        self._txt_explanation.setReadOnly(True)
        self._txt_explanation.setMaximumHeight(80)
        metrics_layout.addWidget(self._txt_explanation)

        right_layout.addWidget(metrics_card)
        right_layout.addStretch()

        splitter.addWidget(right_box)
        splitter.setSizes([450, 550])

        main_layout.addWidget(splitter, 1)

        self._comparisons: list[SignatureComparisonDTO] = []

    def set_comparisons(self, comparisons: list[SignatureComparisonDTO]) -> None:
        """Populate table with signature verification comparisons."""
        self._comparisons = comparisons
        self._table.setRowCount(len(comparisons))

        for row, c in enumerate(comparisons):
            self._table.setItem(row, 0, QTableWidgetItem(c.questioned_doc_name))
            self._table.setItem(row, 1, QTableWidgetItem(c.reference_doc_name))
            self._table.setItem(row, 2, QTableWidgetItem(f"{c.hu_distance:.3f}"))
            self._table.setItem(row, 3, QTableWidgetItem(c.assessment_level.replace("_", " ")))

        if comparisons:
            self._table.selectRow(0)

    def _on_row_selected(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self._comparisons):
            return

        c = self._comparisons[row]
        self._lbl_q_title.setText(f"Questioned: {c.questioned_doc_name}")
        self._lbl_r_title.setText(f"Reference: {c.reference_doc_name}")

        # Load Questioned Crop
        if Path(c.questioned_crop_path).exists():
            pix_q = QPixmap(c.questioned_crop_path)
            if not pix_q.isNull():
                self._lbl_q_img.setPixmap(
                    pix_q.scaled(
                        200, 110,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._lbl_q_img.setText("Invalid Crop")
        else:
            self._lbl_q_img.setText("File Not Found")

        # Load Reference Crop
        if Path(c.reference_crop_path).exists():
            pix_r = QPixmap(c.reference_crop_path)
            if not pix_r.isNull():
                self._lbl_r_img.setPixmap(
                    pix_r.scaled(
                        200, 110,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._lbl_r_img.setText("Invalid Crop")
        else:
            self._lbl_r_img.setText("File Not Found")

        # Verdict Badge & Colors
        verdict = c.assessment_level.replace("_", " ")
        if "IDENTIFICATION" in c.assessment_level:
            color = "#3fb950"
            bg = "#1f4028"
        elif "INCONCLUSIVE" in c.assessment_level:
            color = "#e3b341"
            bg = "#3d3014"
        else:
            color = "#f85149"
            bg = "#491d1e"

        self._lbl_verdict_badge.setText(f"VERDICT: {verdict}")
        self._lbl_verdict_badge.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {color}; padding: 5px 10px; "
            f"background: {bg}; border: 1px solid {color}; border-radius: 4px;"
        )

        self._lbl_hu_distance.setText(
            f"Hu Invariant Moments Distance: <b>{c.hu_distance:.4f}</b>"
        )
        pct = min(100, int(c.hu_distance * 100))
        self._bar_distance.setValue(pct)
        self._lbl_stroke_density.setText(
            f"Stroke Density Ratio: <b>{c.stroke_density_ratio:.2f}</b>"
        )
        self._txt_explanation.setPlainText(c.explanation)
