"""Evidence Inspector dock widget for finding inspection and human adjudication."""

from __future__ import annotations

import logging
import os
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
    """Dock widget for detailed evidence review and human-in-the-loop adjudication."""

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
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)

        self._lbl_title = QLabel("Select a finding to inspect", self._card)
        self._lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        self._lbl_title.setWordWrap(True)
        card_layout.addWidget(self._lbl_title)

        self._lbl_badges = QLabel("", self._card)
        card_layout.addWidget(self._lbl_badges)

        self._lbl_confidence = QLabel("", self._card)
        card_layout.addWidget(self._lbl_confidence)

        layout.addWidget(self._card)

        # 2. Factual Narrative Explanation
        lbl_narrative_hdr = QLabel("FORENSIC NARRATIVE EXPLANATION", content)
        lbl_narrative_hdr.setStyleSheet("font-weight: bold; color: #8e8e9c; font-size: 11px;")
        layout.addWidget(lbl_narrative_hdr)

        self._txt_narrative = QTextEdit(content)
        self._txt_narrative.setReadOnly(True)
        self._txt_narrative.setMaximumHeight(120)
        layout.addWidget(self._txt_narrative)

        # 3. Adjudication History
        lbl_history_hdr = QLabel("ADJUDICATION AUDIT TRAIL", content)
        lbl_history_hdr.setStyleSheet("font-weight: bold; color: #8e8e9c; font-size: 11px;")
        layout.addWidget(lbl_history_hdr)

        self._txt_history = QTextEdit(content)
        self._txt_history.setReadOnly(True)
        self._txt_history.setMaximumHeight(100)
        layout.addWidget(self._txt_history)

        # 4. Human Review Action Box
        review_box = QFrame(content)
        review_box.setObjectName("card")
        review_layout = QVBoxLayout(review_box)
        review_layout.setContentsMargins(10, 10, 10, 10)
        review_layout.setSpacing(8)

        lbl_action_hdr = QLabel("HUMAN REVIEW ADJUDICATION", review_box)
        lbl_action_hdr.setStyleSheet("font-weight: bold; color: #0d6efd; font-size: 11px;")
        review_layout.addWidget(lbl_action_hdr)

        reviewer_layout = QHBoxLayout()
        reviewer_layout.addWidget(QLabel("Reviewer ID:", review_box))
        self._inp_reviewer = QLineEdit("analyst_01", review_box)
        reviewer_layout.addWidget(self._inp_reviewer)
        review_layout.addLayout(reviewer_layout)

        review_layout.addWidget(QLabel("Adjudication Rationale / Notes:", review_box))
        self._txt_rationale = QTextEdit(review_box)
        self._txt_rationale.setPlaceholderText(
            "Enter objective forensic justification for confirming or dismissing this finding..."
        )
        self._txt_rationale.setMaximumHeight(80)
        review_layout.addWidget(self._txt_rationale)

        # Action Buttons
        btn_layout = QHBoxLayout()
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
            self._txt_narrative.setPlainText("")
            self._txt_history.setPlainText("")
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
