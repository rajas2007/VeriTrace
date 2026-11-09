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
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.investigation import FindingResponseDTO
from veritrace.domain.enums.forensic import ReviewDecisionType
from veritrace.gui.components.common import EmptyStateWidget
from veritrace.gui.styles.theme_manager import ThemeManager
from veritrace.gui.styles.tokens import ColorTokens, MetricTokens

logger = logging.getLogger("veritrace.gui.evidence_inspector")


class EvidenceInspectorDock(QDockWidget):
    """Dock widget for detailed evidence review, pixel crop inspection, and human adjudication."""

    review_action_submitted = Signal(
        str, object, str, str
    )  # finding_id, decision, rationale, reviewer_id

    def __init__(self, parent: Any = None) -> None:
        super().__init__("Evidence Inspector", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )

        self._active_finding: FindingResponseDTO | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._stack = QStackedWidget(scroll)

        # 1. Empty State Page (Index 0)
        self._empty_page = EmptyStateWidget(
            headline="Select Discrepancy",
            description=(
                "Select any finding from the Contradiction Matrix to inspect pixel crops, "
                "audit trail, and human adjudication controls."
            ),
            icon_char="🔬",
            parent=self._stack,
        )
        self._stack.addWidget(self._empty_page)

        # 2. Finding Details Page (Index 1)
        self._detail_page = QWidget(self._stack)
        layout = QVBoxLayout(self._detail_page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Overview Card
        self._card = QFrame(self._detail_page)
        self._card.setObjectName("card")
        self._card.setStyleSheet(
            f"background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_MD}; "
            "padding: 6px;"
        )
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)

        self._lbl_title = QLabel("Select a finding to inspect", self._card)
        self._lbl_title.setStyleSheet(
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
            f"font-size: {MetricTokens.FONT_SIZE_BASE}; "
            f"color: {ColorTokens.TEXT_PRIMARY};"
        )
        self._lbl_title.setWordWrap(True)
        card_layout.addWidget(self._lbl_title)

        self._lbl_badges = QLabel("", self._card)
        card_layout.addWidget(self._lbl_badges)

        self._lbl_confidence = QLabel("", self._card)
        self._lbl_confidence.setStyleSheet(
            f"color: {ColorTokens.TEXT_MUTED}; font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        card_layout.addWidget(self._lbl_confidence)

        # Confidence gauge bar
        self._bar_confidence = QProgressBar(self._card)
        self._bar_confidence.setRange(0, 100)
        self._bar_confidence.setValue(0)
        self._bar_confidence.setFixedHeight(6)
        self._bar_confidence.setTextVisible(False)
        self._bar_confidence.setStyleSheet(
            f"QProgressBar {{ background: {ColorTokens.BACKGROUND_BASE}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; border-radius: 3px; }} "
            f"QProgressBar::chunk {{ background: {ColorTokens.ACCENT_PRIMARY}; "
            "border-radius: 2px; }"
        )
        card_layout.addWidget(self._bar_confidence)

        layout.addWidget(self._card)

        # Side-by-Side Visual Evidence Crops Box
        crops_box = QFrame(self._detail_page)
        crops_box.setObjectName("card")
        crops_box.setStyleSheet(
            f"background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_MD}; "
            "padding: 6px;"
        )
        crops_layout = QVBoxLayout(crops_box)
        crops_layout.setContentsMargins(10, 10, 10, 10)
        crops_layout.setSpacing(8)

        lbl_crops_hdr = QLabel("EVIDENCE CROPS", crops_box)
        lbl_crops_hdr.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_SEMIBOLD}; "
            f"color: {ColorTokens.TEXT_MUTED}; "
            "letter-spacing: 0.8px; "
            "text-transform: uppercase;"
        )
        crops_layout.addWidget(lbl_crops_hdr)

        crops_grid = QGridLayout()
        crops_grid.setSpacing(8)

        lbl_q_title = QLabel("Questioned Crop", crops_box)
        lbl_q_title.setStyleSheet(
            f"color: {ColorTokens.TEXT_SECONDARY}; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        crops_grid.addWidget(lbl_q_title, 0, 0)

        lbl_r_title = QLabel("Comparison / ELA Heatmap", crops_box)
        lbl_r_title.setStyleSheet(
            f"color: {ColorTokens.TEXT_SECONDARY}; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        crops_grid.addWidget(lbl_r_title, 0, 1)

        self._lbl_orig_crop = QLabel("No crop available", crops_box)
        self._lbl_orig_crop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_orig_crop.setMinimumSize(95, 70)
        self._lbl_orig_crop.setMaximumHeight(100)
        self._lbl_orig_crop.setStyleSheet(
            f"background-color: {ColorTokens.BACKGROUND_BASE}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_SM}; "
            f"color: {ColorTokens.TEXT_MUTED}; font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        crops_grid.addWidget(self._lbl_orig_crop, 1, 0)

        self._lbl_ela_crop = QLabel("No crop available", crops_box)
        self._lbl_ela_crop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ela_crop.setMinimumSize(95, 70)
        self._lbl_ela_crop.setMaximumHeight(100)
        self._lbl_ela_crop.setStyleSheet(
            f"background-color: {ColorTokens.BACKGROUND_BASE}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_SM}; "
            f"color: {ColorTokens.TEXT_MUTED}; font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        crops_grid.addWidget(self._lbl_ela_crop, 1, 1)

        crops_layout.addLayout(crops_grid)
        layout.addWidget(crops_box)

        # Forensic Narrative Explanation
        lbl_narrative_hdr = QLabel("FORENSIC NARRATIVE", self._detail_page)
        lbl_narrative_hdr.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_SEMIBOLD}; "
            f"color: {ColorTokens.TEXT_MUTED}; "
            "letter-spacing: 0.8px; "
            "text-transform: uppercase;"
        )
        layout.addWidget(lbl_narrative_hdr)

        self._txt_narrative = QTextEdit(self._detail_page)
        self._txt_narrative.setReadOnly(True)
        self._txt_narrative.setMaximumHeight(85)
        layout.addWidget(self._txt_narrative)

        # Adjudication History
        lbl_history_hdr = QLabel("AUDIT TRAIL", self._detail_page)
        lbl_history_hdr.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_SEMIBOLD}; "
            f"color: {ColorTokens.TEXT_MUTED}; "
            "letter-spacing: 0.8px; "
            "text-transform: uppercase;"
        )
        layout.addWidget(lbl_history_hdr)

        self._txt_history = QTextEdit(self._detail_page)
        self._txt_history.setReadOnly(True)
        self._txt_history.setMaximumHeight(70)
        layout.addWidget(self._txt_history)

        # Human Review Action Box
        review_box = QFrame(self._detail_page)
        review_box.setObjectName("card")
        review_box.setStyleSheet(
            f"background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_MD}; "
            "padding: 6px;"
        )
        review_layout = QVBoxLayout(review_box)
        review_layout.setContentsMargins(10, 10, 10, 10)
        review_layout.setSpacing(8)

        lbl_action_hdr = QLabel("HUMAN REVIEW ADJUDICATION", review_box)
        lbl_action_hdr.setStyleSheet(
            f"font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_SEMIBOLD}; "
            f"color: {ColorTokens.TEXT_MUTED}; "
            "letter-spacing: 0.8px; "
            "text-transform: uppercase;"
        )
        review_layout.addWidget(lbl_action_hdr)

        reviewer_layout = QHBoxLayout()
        reviewer_layout.setSpacing(8)
        lbl_rev = QLabel("Reviewer:", review_box)
        lbl_rev.setStyleSheet(
            f"color: {ColorTokens.TEXT_SECONDARY}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM}; "
            f"font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        reviewer_layout.addWidget(lbl_rev)
        self._inp_reviewer = QLineEdit("analyst_01", review_box)
        reviewer_layout.addWidget(self._inp_reviewer)
        review_layout.addLayout(reviewer_layout)

        lbl_notes = QLabel("Justification / Rationale:", review_box)
        lbl_notes.setStyleSheet(
            f"color: {ColorTokens.TEXT_SECONDARY}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM}; "
            f"font-size: {MetricTokens.FONT_SIZE_XS};"
        )
        review_layout.addWidget(lbl_notes)

        self._txt_rationale = QTextEdit(review_box)
        self._txt_rationale.setPlaceholderText(
            "Enter objective forensic justification for confirming or dismissing this finding..."
        )
        self._txt_rationale.setMaximumHeight(55)
        review_layout.addWidget(self._txt_rationale)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._btn_confirm = QPushButton("Confirm", review_box)
        self._btn_confirm.setObjectName("confirmButton")
        self._btn_confirm.setStyleSheet(
            f"background-color: {ColorTokens.SEVERITY_LOW_TINT}; "
            f"color: {ColorTokens.SEVERITY_LOW}; "
            f"border: 1px solid rgba(79, 209, 165, 0.3); "
            f"font-weight: {MetricTokens.FONT_WEIGHT_SEMIBOLD}; padding: 6px 12px;"
        )
        self._btn_confirm.clicked.connect(self._on_confirm_clicked)
        btn_layout.addWidget(self._btn_confirm)

        self._btn_dismiss = QPushButton("Dismiss", review_box)
        self._btn_dismiss.setObjectName("dismissButton")
        self._btn_dismiss.setStyleSheet(
            f"background-color: {ColorTokens.SEVERITY_CRITICAL_TINT}; "
            f"color: {ColorTokens.SEVERITY_CRITICAL}; "
            f"border: 1px solid rgba(240, 97, 109, 0.3); "
            f"font-weight: {MetricTokens.FONT_WEIGHT_SEMIBOLD}; padding: 6px 12px;"
        )
        self._btn_dismiss.clicked.connect(self._on_dismiss_clicked)
        btn_layout.addWidget(self._btn_dismiss)

        self._btn_note = QPushButton("Add Note", review_box)
        self._btn_note.setObjectName("secondaryButton")
        self._btn_note.setStyleSheet(
            f"padding: 6px 12px; font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        self._btn_note.clicked.connect(self._on_annotate_clicked)
        btn_layout.addWidget(self._btn_note)

        review_layout.addLayout(btn_layout)
        layout.addWidget(review_box)

        layout.addStretch()
        self._stack.addWidget(self._detail_page)

        scroll.setWidget(self._stack)
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
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)
        self._btn_confirm.setEnabled(True)
        self._btn_dismiss.setEnabled(True)
        self._btn_note.setEnabled(True)

        self._lbl_title.setText(finding.title)

        sev_badge = ThemeManager.format_severity_pill(finding.severity.value)
        tier_badge = ThemeManager.format_tier_pill(finding.epistemic_tier.value)
        status_badge = ThemeManager.format_status_pill(finding.review_status.value)

        self._lbl_badges.setText(f"{sev_badge}  {tier_badge}  {status_badge}")
        self._lbl_confidence.setText(
            f"Confidence: <b>{finding.confidence * 100:.1f}%</b>  |  "
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
                    110,
                    80,
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
                    110,
                    80,
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
