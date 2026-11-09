"""Custom status bar with progress telemetry and execution tracking."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QStatusBar,
    QWidget,
)

from veritrace.gui.styles.tokens import ColorTokens, MetricTokens


class VeriTraceStatusBar(QStatusBar):
    """Forensic status bar displaying stage telemetry and task progress."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet(
            f"QStatusBar {{ background-color: {ColorTokens.SURFACE_SIDEBAR}; "
            f"border-top: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"color: {ColorTokens.TEXT_MUTED}; }}"
        )

        self._container = QWidget(self)
        layout = QHBoxLayout(self._container)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(12)

        self._stage_badge = QLabel("IDLE", self)
        self._stage_badge.setStyleSheet(
            f"background-color: {ColorTokens.SEVERITY_LOW_TINT}; "
            f"color: {ColorTokens.SEVERITY_LOW}; "
            "border: 1px solid rgba(79, 209, 165, 0.3); "
            f"padding: 1px 6px; border-radius: {MetricTokens.RADIUS_SM}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
            f"font-size: 10px; font-family: {MetricTokens.FONT_FAMILY_MONO};"
        )
        layout.addWidget(self._stage_badge)

        self._status_label = QLabel("Ready", self)
        self._status_label.setStyleSheet(
            f"color: {ColorTokens.TEXT_SECONDARY}; "
            f"font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedWidth(180)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ background: {ColorTokens.BACKGROUND_BASE}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; border-radius: 3px; }} "
            f"QProgressBar::chunk {{ background: {ColorTokens.ACCENT_PRIMARY}; "
            "border-radius: 2px; }"
        )
        layout.addWidget(self._progress_bar)

        self._telemetry_label = QLabel("", self)
        self._telemetry_label.setStyleSheet(
            f"color: {ColorTokens.TEXT_MUTED}; font-size: 10px; "
            f"font-family: {MetricTokens.FONT_FAMILY_MONO};"
        )
        layout.addWidget(self._telemetry_label)

        self.addPermanentWidget(self._container, 1)

    def set_status(self, message: str, stage: str = "READY") -> None:
        """Update status message and stage indicator."""
        self._status_label.setText(message)
        self._stage_badge.setText(stage.upper())
        if stage.upper() in ("READY", "IDLE"):
            self._stage_badge.setStyleSheet(
                f"background-color: {ColorTokens.SEVERITY_LOW_TINT}; "
                f"color: {ColorTokens.SEVERITY_LOW}; "
                "border: 1px solid rgba(79, 209, 165, 0.3); "
                f"padding: 1px 6px; border-radius: {MetricTokens.RADIUS_SM}; "
                f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
                f"font-size: 10px; font-family: {MetricTokens.FONT_FAMILY_MONO};"
            )
        elif stage.upper() in ("ANALYZING", "PROCESSING"):
            self._stage_badge.setStyleSheet(
                f"background-color: {ColorTokens.ACCENT_MUTED}; "
                f"color: {ColorTokens.ACCENT_PRIMARY}; "
                "border: 1px solid rgba(91, 140, 255, 0.3); "
                f"padding: 1px 6px; border-radius: {MetricTokens.RADIUS_SM}; "
                f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
                f"font-size: 10px; font-family: {MetricTokens.FONT_FAMILY_MONO};"
            )
        elif stage.upper() == "ERROR":
            self._stage_badge.setStyleSheet(
                f"background-color: {ColorTokens.SEVERITY_CRITICAL_TINT}; "
                f"color: {ColorTokens.SEVERITY_CRITICAL}; "
                "border: 1px solid rgba(240, 97, 109, 0.3); "
                f"padding: 1px 6px; border-radius: {MetricTokens.RADIUS_SM}; "
                f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD}; "
                f"font-size: 10px; font-family: {MetricTokens.FONT_FAMILY_MONO};"
            )

    def start_progress(self, message: str = "Processing...") -> None:
        """Show progress bar and update stage to PROCESSING."""
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self.set_status(message, stage="ANALYZING")

    def update_progress(self, percent: int, message: str) -> None:
        """Update progress value and status message."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    def finish_progress(self, message: str = "Operation completed") -> None:
        """Hide progress bar and set stage to READY."""
        self._progress_bar.setValue(100)
        self._progress_bar.setVisible(False)
        self.set_status(message, stage="READY")

    def set_telemetry(self, text: str) -> None:
        """Set telemetry or case metadata string."""
        self._telemetry_label.setText(text)
