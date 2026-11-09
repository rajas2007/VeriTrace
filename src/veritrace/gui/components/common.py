"""Reusable UI components for VeriTrace.

Includes:
- StatCard: Linear-style metric card with tabular numerals and semantic accent dots
- ToggleSwitch: Modern smooth pill toggle switch
- EmptyStateWidget: Enterprise-grade placeholder for empty matrices and viewers
- CommandPaletteDialog: Ctrl+K Raycast-style command launcher
- ToastNotification: Bottom-right non-blocking notification pill
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from veritrace.gui.styles.tokens import ColorTokens, MetricTokens


# ---------------------------------------------------------------------------
# 1. StatCard Component
# ---------------------------------------------------------------------------
class StatCard(QFrame):
    """Linear/Bloomberg-grade stat card with tabular numerals and dot indicator."""

    def __init__(
        self,
        label: str,
        value: str = "0",
        color: str = ColorTokens.ACCENT_PRIMARY,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(85)
        self.setStyleSheet(
            f"QFrame#card {{ background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_MD}; }}"
            f"QFrame#card:hover {{ border-color: {ColorTokens.BORDER_FOCUS}; "
            f"background-color: {ColorTokens.SURFACE_HOVER}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header with subtle colored dot + uppercase label
        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        header_row.setContentsMargins(0, 0, 0, 0)

        self._dot = QLabel(self)
        self._dot.setFixedSize(6, 6)
        self._dot.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
        header_row.addWidget(self._dot)

        self._lbl_label = QLabel(label, self)
        self._lbl_label.setStyleSheet(
            f"color: {ColorTokens.TEXT_MUTED}; font-size: 10px; font-weight: 600; "
            f"letter-spacing: 0.05em; text-transform: uppercase;"
        )
        header_row.addWidget(self._lbl_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Value display (large tabular numerals)
        self._lbl_value = QLabel(value, self)
        self._lbl_value.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {ColorTokens.TEXT_PRIMARY}; "
            f"font-family: {MetricTokens.FONT_FAMILY_MONO}; padding-top: 1px;"
        )
        layout.addWidget(self._lbl_value)

    def set_value(self, value: str | int) -> None:
        """Update counter value."""
        self._lbl_value.setText(str(value))


# ---------------------------------------------------------------------------
# 2. ToggleSwitch Component
# ---------------------------------------------------------------------------
class ToggleSwitch(QWidget):
    """Modern iOS / Linear-style pill toggle switch."""

    toggled = Signal(bool)

    def __init__(self, text: str = "", parent: Any = None) -> None:
        super().__init__(parent)
        self._text = text
        self._checked = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked != checked:
            self._checked = checked
            self.toggled.emit(self._checked)
            self.update()

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self.update()

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def sizeHint(self) -> QSize:
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self._text) if self._text else 0
        return QSize(40 + (text_width + 8 if text_width else 0), 24)

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Switch pill track (34x18)
        track_rect = QRectF(0, 3, 34, 18)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, 9, 9)

        if self._checked:
            painter.fillPath(track_path, QColor(ColorTokens.ACCENT_PRIMARY))
            thumb_x = 18.0
        else:
            painter.fillPath(track_path, QColor(ColorTokens.BORDER_SUBTLE))
            thumb_x = 2.0

        # Thumb circle
        thumb_rect = QRectF(thumb_x, 5, 14, 14)
        thumb_path = QPainterPath()
        thumb_path.addEllipse(thumb_rect)
        painter.fillPath(
            thumb_path,
            QColor("#FFFFFF" if self._checked else ColorTokens.TEXT_SECONDARY),
        )

        # Text label
        if self._text:
            painter.setPen(
                QColor(ColorTokens.TEXT_PRIMARY if self._checked else ColorTokens.TEXT_SECONDARY)
            )
            font = QFont(MetricTokens.FONT_FAMILY_SANS, 11, QFont.Weight.Medium)
            painter.setFont(font)
            painter.drawText(
                QRectF(42, 0, self.width() - 42, 24),
                Qt.AlignmentFlag.AlignVCenter,
                self._text,
            )


# ---------------------------------------------------------------------------
# 3. EmptyStateWidget Component
# ---------------------------------------------------------------------------
class EmptyStateWidget(QWidget):
    """Refined empty state with icon, headline, supportive text, and CTA."""

    action_requested = Signal()
    cta_clicked = Signal()

    def __init__(
        self,
        headline: str = "",
        description: str = "",
        icon_char: str = "🔍",
        cta_text: str = "",
        parent: Any = None,
        title: str = "",
        action_text: str = "",
    ) -> None:
        super().__init__(parent)
        final_title = headline or title or "No Records Found"
        final_action = cta_text or action_text

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(24, 32, 24, 32)
        layout.setSpacing(10)

        # Icon circle
        icon_circle = QFrame(self)
        icon_circle.setFixedSize(48, 48)
        icon_circle.setStyleSheet(
            f"background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            "border-radius: 24px;"
        )
        icon_inner = QLabel(icon_char, icon_circle)
        icon_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_inner.setGeometry(0, 0, 48, 48)
        icon_inner.setStyleSheet("font-size: 20px; background: transparent;")
        layout.addWidget(icon_circle, 0, Qt.AlignmentFlag.AlignCenter)

        # Title
        lbl_title = QLabel(final_title, self)
        lbl_title.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {ColorTokens.TEXT_PRIMARY};"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # Description
        lbl_desc = QLabel(description, self)
        lbl_desc.setStyleSheet(
            f"font-size: 12px; color: {ColorTokens.TEXT_MUTED}; max-width: 380px;"
        )
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Optional Action CTA
        if final_action:
            layout.addSpacing(6)
            btn = QPushButton(final_action, self)
            btn.setObjectName("primaryButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("padding: 7px 16px; font-size: 12px; font-weight: 600;")
            btn.clicked.connect(self._on_action_clicked)
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

    def _on_action_clicked(self) -> None:
        self.action_requested.emit()
        self.cta_clicked.emit()


# ---------------------------------------------------------------------------
# 4. CommandPaletteDialog (Ctrl+K)
# ---------------------------------------------------------------------------
class CommandPaletteDialog(QDialog):
    """Raycast / Linear style Ctrl+K command palette."""

    action_triggered = Signal(str)

    def __init__(
        self,
        commands: list[tuple[str, str, Any]] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(540, 360)
        self.setStyleSheet(
            f"QDialog {{ background-color: {ColorTokens.SURFACE_SIDEBAR}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; border-radius: 8px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Search bar
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Type a command or search action (ESC to close)...")
        self._search.setStyleSheet(
            f"background-color: {ColorTokens.BACKGROUND_BASE}; color: {ColorTokens.TEXT_PRIMARY}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; border-radius: 6px; "
            "padding: 9px 12px; font-size: 13px;"
        )
        self._search.textChanged.connect(self._filter_commands)
        layout.addWidget(self._search)

        # Results list
        self._list = QListWidget(self)
        self._list.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; outline: none; }} "
            f"QListWidget::item {{ padding: 8px 12px; border-radius: 6px; "
            f"color: {ColorTokens.TEXT_SECONDARY}; }} "
            f"QListWidget::item:selected {{ background-color: {ColorTokens.SURFACE_HOVER}; "
            f"color: {ColorTokens.TEXT_PRIMARY}; }}"
        )
        self._list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._list)

        if commands is not None:
            self._commands = commands
        else:
            self._commands = [
                (
                    "⚡ Run Full Forensics",
                    "Run deterministic cross-document correlation and heuristics",
                    "run_forensics",
                ),
                (
                    "📄 Export PS-2 Dossier (PDF)",
                    "Generate court-ready 6-section forensic PDF report",
                    "export_pdf",
                ),
                (
                    "📊 Export JSON Intelligence Payload",
                    "Compile structured JSON evidence dossier",
                    "export_json",
                ),
                (
                    "✍️ Open Signature Workbench",
                    "Navigate to signature detection & Hu moment analyzer",
                    "tab_signatures",
                ),
                (
                    "🧮 Open Math & Chronology Audit",
                    "Navigate to arithmetic checks and delivery sequence audit",
                    "tab_audit",
                ),
                (
                    "🔍 Open Contradiction Matrix",
                    "View cross-document inconsistency table",
                    "tab_matrix",
                ),
                (
                    "📸 Open Side-by-Side Canvas",
                    "View document comparators and ELA heatmaps",
                    "tab_canvas",
                ),
                (
                    "📥 Import Case Document",
                    "Ingest purchase order, challan, MTC, or invoice",
                    "import_doc",
                ),
                (
                    "🔄 Reload Industrial Demo",
                    "Load 4-document alloy fraud demonstration case",
                    "load_demo",
                ),
            ]
        self._populate()

    def _populate(self, filter_text: str = "") -> None:
        self._list.clear()
        query = filter_text.strip().lower()
        for idx, item_data in enumerate(self._commands):
            title = item_data[0]
            desc = item_data[1]
            if not query or query in title.lower() or query in desc.lower():
                item = QListWidgetItem(f"{title}  —  {desc}")
                item.setData(Qt.ItemDataRole.UserRole, idx)
                self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _filter_commands(self, text: str) -> None:
        self._populate(text)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self._commands):
            handler = self._commands[idx][2]
            if callable(handler):
                self.accept()
                handler()
                return
            elif isinstance(handler, str):
                self.action_triggered.emit(handler)
        self.accept()


# ---------------------------------------------------------------------------
# 5. ToastNotification Component
# ---------------------------------------------------------------------------
class ToastNotification(QFrame):
    """Floating non-blocking notification pill placed in bottom-right."""

    def __init__(self, message: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(
            f"QFrame#card {{ background-color: {ColorTokens.SURFACE_CARD}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; border-radius: 6px; "
            f"color: {ColorTokens.TEXT_PRIMARY}; font-size: 12px; font-weight: 500; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        icon_lbl = QLabel("✓", self)
        icon_lbl.setStyleSheet(f"color: {ColorTokens.SEVERITY_LOW}; font-weight: 700;")
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message, self)
        layout.addWidget(msg_lbl)

        self.adjustSize()

    @classmethod
    def show_toast(
        cls, parent: QWidget, message: str, duration_ms: int = 2500
    ) -> ToastNotification:
        """Create and animate a toast message in parent window."""
        toast = cls(message, parent)
        toast.show()
        # Position in bottom-right corner of parent
        pw = parent.width()
        ph = parent.height()
        tw = toast.width()
        th = toast.height()
        toast.move(pw - tw - 20, ph - th - 36)
        toast.raise_()
        QTimer.singleShot(duration_ms, toast.deleteLater)
        return toast
