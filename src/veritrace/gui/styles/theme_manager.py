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
    "CRITICAL": "#dc3545",
    "HIGH": "#fd7e14",
    "MEDIUM": "#ffc107",
    "LOW": "#6c757d",
}

STATUS_COLORS: dict[str, str] = {
    "CONFIRMED": "#198754",
    "DISMISSED": "#6c757d",
    "PENDING_REVIEW": "#0d6efd",
    "ANNOTATED": "#6f42c1",
}

TIER_COLORS: dict[str, str] = {
    "CONFIRMED_OBSERVATION": "#20c997",
    "DETECTED_INCONSISTENCY": "#fd7e14",
    "SUSPECTED_MANIPULATION": "#dc3545",
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
        return SEVERITY_COLORS.get(severity.upper(), "#6c757d")

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """Return hex color code for a review status."""
        return STATUS_COLORS.get(status.upper(), "#6c757d")

    @classmethod
    def get_tier_color(cls, tier: str) -> str:
        """Return hex color code for an epistemic tier."""
        return TIER_COLORS.get(tier.upper(), "#fd7e14")

    @classmethod
    def format_badge_html(cls, text: str, bg_color: str, fg_color: str = "#ffffff") -> str:
        """Return styled HTML span badge."""
        return (
            f"<span style='background-color: {bg_color}; color: {fg_color}; "
            f"padding: 2px 8px; border-radius: 3px; font-weight: bold; font-size: 11px;'>"
            f"{text}</span>"
        )
