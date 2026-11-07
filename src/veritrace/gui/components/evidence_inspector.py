"""Evidence Inspector dock widget for finding inspection and human adjudication."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.investigation import FindingResponseDTO
from veritrace.domain.enums.forensic import ReviewDecisionType
from veritrace.gui.styles.theme_manager import ThemeManager

logger = logging.getLogger("veritrace.gui.evidence_inspector")


class EvidenceInspectorDock(QDockWidget):
    """Dock widget for detailed evidence review, pixel crop inspection, and human adjudication."""

    review_action_submitted = Signal(
        str, object, str, str
    )  # finding_id, decision, rationale, reviewer_id

    def __init__(self, parent: Any = None) -> None:
        super().__init__("EVIDENCE INSPECTOR & ADJUDICATION", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )

        self._active_finding: FindingResponseDTO | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Finding Overview Card
        self._card = QFrame(content)
        self._card.setObjectName("card")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        self._lbl_title = QLabel("Select a finding to inspect", self._card)
        self._lbl_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #f1f5f9;")
        self._lbl_title.setWordWrap(True)
        card_layout.addWidget(self._lbl_title)

        self._lbl_badges = QLabel("", self._card)
        card_layout.addWidget(self._lbl_badges)

        self._lbl_confidence = QLabel("", self._card)
        self._lbl_confidence.setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_layout.addWidget(self._lbl_confidence)

        # Confidence gauge bar
        self._bar_confidence = QProgressBar(self._card)
        self._bar_confidence.setRange(0, 100)
        self._bar_confidence.setValue(0)
        self._bar_confidence.setFixedHeight(8)
        self._bar_confidence.setTextVisible(False)
        self._bar_confidence.setStyleSheet(
            "QProgressBar { background: #06090f; border: 1px solid #1c2438; "
            "border-radius: 4px; } "
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #1d4ed8, stop:1 #06b6d4); border-radius: 3px; }"
        )
        card_layout.addWidget(self._bar_confidence)

        layout.addWidget(self._card)

        # 2. Side-by-Side Visual Evidence Crops Box
        crops_box = QFrame(content)
        crops_box.setObjectName("card")
        crops_layout = QVBoxLayout(crops_box)
        crops_layout.setContentsMargins(10, 10, 10, 10)
        crops_layout.setSpacing(8)

        lbl_crops_hdr = QLabel("PIXEL-ANCHORED EVIDENCE CROPS", crops_box)
        lbl_crops_hdr.setStyleSheet(
            "font-weight: 700; color: #38bdf8; font-size: 11px; letter-spacing: 0.5px;"
        )
        crops_layout.addWidget(lbl_crops_hdr)

        crops_grid = QGridLayout()
        crops_grid.setSpacing(8)

        lbl_q_title = QLabel("Questioned Crop", crops_box)
        lbl_q_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700;")
        crops_grid.addWidget(lbl_q_title, 0, 0)

        lbl_r_title = QLabel("Comparison / ELA Heatmap", crops_box)
        lbl_r_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700;")
        crops_grid.addWidget(lbl_r_title, 0, 1)

        self._lbl_orig_crop = QLabel("No crop available", crops_box)
        self._lbl_orig_crop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_orig_crop.setMinimumSize(130, 95)
        self._lbl_orig_crop.setMaximumHeight(125)
        self._lbl_orig_crop.setStyleSheet(
            "background-color: #06090f; border: 1px solid #1c2438; "
            "border-radius: 6px; color: #64748b; font-size: 11px;"
        )
        crops_grid.addWidget(self._lbl_orig_crop, 1, 0)

        self._lbl_ela_crop = QLabel("No crop available", crops_box)
        self._lbl_ela_crop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ela_crop.setMinimumSize(130, 95)
        self._lbl_ela_crop.setMaximumHeight(125)
        self._lbl_ela_crop.setStyleSheet(
            "background-color: #06090f; border: 1px solid #1c2438; "
            "border-radius: 6px; color: #64748b; font-size: 11px;"
        )
        crops_grid.addWidget(self._lbl_ela_crop, 1, 1)

        crops_layout.addLayout(crops_grid)
        layout.addWidget(crops_box)

        # 3. Factual Narrative Explanation
        lbl_narrative_hdr = QLabel("FORENSIC NARRATIVE EXPLANATION", content)
        lbl_narrative_hdr.setStyleSheet(
            "font-weight: 700; color: #94a3b8; font-size: 11px; letter-spacing: 0.5px;"
        )
        layout.addWidget(lbl_narrative_hdr)

        self._txt_narrative = QTextEdit(content)
        self._txt_narrative.setReadOnly(True)
        self._txt_narrative.setMaximumHeight(110)
        layout.addWidget(self._txt_narrative)

        # 4. Adjudication History
        lbl_history_hdr = QLabel("ADJUDICATION AUDIT TRAIL", content)
        lbl_history_hdr.setStyleSheet(
            "font-weight: 700; color: #94a3b8; font-size: 11px; letter-spacing: 0.5px;"
        )
        layout.addWidget(lbl_history_hdr)

        self._txt_history = QTextEdit(content)
        self._txt_history.setReadOnly(True)
        self._txt_history.setMaximumHeight(90)
        layout.addWidget(self._txt_history)

        # 5. Human Review Action Box
        review_box = QFrame(content)
        review_box.setObjectName("card")
        review_layout = QVBoxLayout(review_box)
        review_layout.setContentsMargins(10, 10, 10, 10)
        review_layout.setSpacing(8)

        lbl_action_hdr = QLabel("HUMAN REVIEW ADJUDICATION", review_box)
        lbl_action_hdr.setStyleSheet(
            "font-weight: 700; color: #38bdf8; font-size: 11px; letter-spacing: 0.5px;"
        )
        review_layout.addWidget(lbl_action_hdr)

        reviewer_layout = QHBoxLayout()
        lbl_rev = QLabel("Reviewer ID:", review_box)
        lbl_rev.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        reviewer_layout.addWidget(lbl_rev)
        self._inp_reviewer = QLineEdit("analyst_01", review_box)
        reviewer_layout.addWidget(self._inp_reviewer)
        review_layout.addLayout(reviewer_layout)

        lbl_notes = QLabel("Adjudication Rationale / Notes:", review_box)
        lbl_notes.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        review_layout.addWidget(lbl_notes)

        self._txt_rationale = QTextEdit(review_box)
        self._txt_rationale.setPlaceholderText(
            "Enter objective forensic justification for confirming or dismissing this finding..."
        )
        self._txt_rationale.setMaximumHeight(70)
        review_layout.addWidget(self._txt_rationale)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._btn_confirm = QPushButton("Confirm", review_box)
        self._btn_confirm.setObjectName("confirmButton")
        self._btn_confirm.clicked.connect(self._on_confirm_clicked)
        btn_layout.addWidget(self._btn_confirm)

        self._btn_dismiss = QPushButton("Dismiss", review_box)
        self._btn_dismiss.setObjectName("dismissButton")
        self._btn_dismiss.clicked.connect(self._on_dismiss_clicked)
        btn_layout.addWidget(self._btn_dismiss)

        self._btn_note = QPushButton("Add Note", review_box)
        self._btn_note.clicked.connect(self._on_annotate_clicked)
        btn_layout.addWidget(self._btn_note)

        review_layout.addLayout(btn_layout)
        layout.addWidget(review_box)

        layout.addStretch()
        scroll.setWidget(content)
        self.setWidget(scroll)

    def set_finding(self, finding: FindingResponseDTO | None) -> None:
        """Bind finding details to inspector dock."""
        self._active_finding = finding
        if not finding:
            self._lbl_title.setText("Select a finding to inspect")
            self._lbl_badges.setText("")
            self._lbl_confidence.setText("")
            self._bar_confidence.setValue(0)
            self._txt_narrative.setPlainText("")
            self._txt_history.setPlainText("")
            self._lbl_orig_crop.setText("No crop available")
            self._lbl_orig_crop.setPixmap(QPixmap())
            self._lbl_ela_crop.setText("No crop available")
            self._lbl_ela_crop.setPixmap(QPixmap())
            self._btn_confirm.setEnabled(False)
            self._btn_dismiss.setEnabled(False)
            self._btn_note.setEnabled(False)
            return

        self._btn_confirm.setEnabled(True)
        self._btn_dismiss.setEnabled(True)
        self._btn_note.setEnabled(True)

        self._lbl_title.setText(finding.title)

        sev_badge = ThemeManager.format_badge_html(
            finding.severity.value,
            ThemeManager.get_severity_color(finding.severity.value),
        )
        tier_badge = ThemeManager.format_badge_html(
            finding.epistemic_tier.value.replace("_", " "),
            ThemeManager.get_tier_color(finding.epistemic_tier.value),
        )
        status_badge = ThemeManager.format_badge_html(
            finding.review_status.value,
            ThemeManager.get_status_color(finding.review_status.value),
        )

        self._lbl_badges.setText(f"{sev_badge} {tier_badge} {status_badge}")
        self._lbl_confidence.setText(
            f"Confidence: <b>{finding.confidence * 100:.1f}%</b> | "
            f"Category: <b>{finding.category.value}</b>"
        )
        self._bar_confidence.setValue(int(finding.confidence * 100))

        self._txt_narrative.setPlainText(finding.narrative_explanation)

        # Adjudication history
        if finding.review_decisions:
            lines = []
            for d in finding.review_decisions:
                lines.append(
                    f"[{d.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}] {d.reviewer_id} -> "
                    f"{d.decision.value}: {d.rationale}"
                )
            self._txt_history.setPlainText("\n".join(lines))
        else:
            self._txt_history.setPlainText("No prior review adjudications recorded.")

    def set_crops(
        self,
        orig_crop_path: str | None = None,
        ela_crop_path: str | None = None,
    ) -> None:
        """Render high-resolution visual evidence crops in the inspector."""
        if orig_crop_path and Path(orig_crop_path).exists():
            pix = QPixmap(orig_crop_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    140,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._lbl_orig_crop.setPixmap(scaled)
            else:
                self._lbl_orig_crop.setText("Invalid Image")
        else:
            self._lbl_orig_crop.setPixmap(QPixmap())
            self._lbl_orig_crop.setText("No crop on disk")

        if ela_crop_path and Path(ela_crop_path).exists():
            pix_ela = QPixmap(ela_crop_path)
            if not pix_ela.isNull():
                scaled_ela = pix_ela.scaled(
                    140,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._lbl_ela_crop.setPixmap(scaled_ela)
            else:
                self._lbl_ela_crop.setText("Invalid Heatmap")
        else:
            self._lbl_ela_crop.setPixmap(QPixmap())
            self._lbl_ela_crop.setText("No ELA heatmap")

    def _on_confirm_clicked(self) -> None:
        self._submit_review(ReviewDecisionType.CONFIRMED)

    def _on_dismiss_clicked(self) -> None:
        self._submit_review(ReviewDecisionType.DISMISSED)

    def _on_annotate_clicked(self) -> None:
        self._submit_review(ReviewDecisionType.ANNOTATED)

    def _submit_review(self, decision: ReviewDecisionType) -> None:
        if not self._active_finding:
            return

        rationale = self._txt_rationale.toPlainText().strip()
        if not rationale:
            if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
                logger.warning("Adjudication rationale is empty; skipping modal in offscreen")
                return
            QMessageBox.warning(
                self,
                "Rationale Required",
                "Human review adjudication requires a mandatory factual rationale/justification.",
            )
            return

        reviewer_id = self._inp_reviewer.text().strip() or "analyst_01"
        self.review_action_submitted.emit(
            self._active_finding.id,
            decision,
            rationale,
            reviewer_id,
        )
        self._txt_rationale.clear()
