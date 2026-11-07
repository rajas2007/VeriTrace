"""VeriTrace UI Theme Manager.

Provides helpers to locate, read, and apply QSS stylesheets to
PySide6 QApplication and top-level QWidget hierarchies, along with
epistemic tier, severity, and review status badge formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("veritrace.gui.styles.theme_manager")

CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_QSS_PATH = CURRENT_DIR / "dark_theme.qss"

SEVERITY_COLORS: dict[str, str] = {
    "CRITICAL": "#ef4444",
    "HIGH": "#f97316",
    "MEDIUM": "#eab308",
    "LOW": "#64748b",
}

STATUS_COLORS: dict[str, str] = {
    "CONFIRMED": "#10b981",
    "DISMISSED": "#64748b",
    "PENDING_REVIEW": "#3b82f6",
    "ANNOTATED": "#a855f7",
}

TIER_COLORS: dict[str, str] = {
    "CONFIRMED_OBSERVATION": "#06b6d4",
    "DETECTED_INCONSISTENCY": "#f97316",
    "SUSPECTED_MANIPULATION": "#ef4444",
}


def get_theme_path(theme_name: str = "dark_theme") -> Path:
    """Return the absolute path to a named QSS theme file.

    Args:
        theme_name: Base filename without extension (defaults to 'dark_theme').

    Returns:
        Path object pointing to the stylesheet file.
    """
    candidate = CURRENT_DIR / f"{theme_name}.qss"
    if candidate.is_file():
        return candidate
    return DEFAULT_QSS_PATH


def load_stylesheet(theme_name: str = "dark_theme") -> str:
    """Read and return stylesheet content for the requested theme.

    Args:
        theme_name: Base filename without extension.

    Returns:
        String containing the CSS/QSS rules.
    """
    path = get_theme_path(theme_name)
    if not path.is_file():
        logger.warning("Theme file not found at %s. Returning empty stylesheet.", path)
        return ""

    try:
        content = path.read_text(encoding="utf-8")
        logger.debug("Successfully loaded theme stylesheet from %s (%d chars)", path, len(content))
        return content
    except OSError as err:
        logger.error("Failed to read theme file %s: %s", path, err)
        return ""


class ThemeManager:
    """Manages Qt dark theme stylesheet loading and badge formatting."""

    _stylesheet: str | None = None

    @classmethod
    def get_stylesheet(cls, theme_name: str = "dark_theme") -> str:
        """Load and return the QSS dark theme stylesheet."""
        if cls._stylesheet is None:
            cls._stylesheet = load_stylesheet(theme_name)
        return cls._stylesheet

    @classmethod
    def get_severity_color(cls, severity: str) -> str:
        """Return hex color code for a severity level."""
        return SEVERITY_COLORS.get(severity.upper(), "#64748b")

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """Return hex color code for a review status."""
        return STATUS_COLORS.get(status.upper(), "#64748b")

    @classmethod
    def get_tier_color(cls, tier: str) -> str:
        """Return hex color code for an epistemic tier."""
        return TIER_COLORS.get(tier.upper(), "#f97316")

    @classmethod
    def format_badge_html(cls, text: str, bg_color: str, fg_color: str = "#ffffff") -> str:
        """Return styled HTML span badge."""
        return (
            f"<span style='background-color: {bg_color}; color: {fg_color}; "
            f"padding: 3px 9px; border-radius: 9px; font-weight: 700; font-size: 11px; "
            f"letter-spacing: 0.3px;'>"
            f"{text}</span>"
        )
