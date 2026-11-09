"""VeriTrace UI Theme Manager.

Provides helpers to locate, read, and apply QSS stylesheets to
PySide6 QApplication and top-level QWidget hierarchies, along with
epistemic tier, severity, and review status badge formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path

from veritrace.gui.styles.tokens import ColorTokens, format_pill_html

logger = logging.getLogger("veritrace.gui.styles.theme_manager")

CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_QSS_PATH = CURRENT_DIR / "dark_theme.qss"

# Linear/Vercel-inspired desaturated semantic colors
SEVERITY_COLORS: dict[str, str] = {
    "CRITICAL": ColorTokens.CRITICAL_FG,
    "HIGH": ColorTokens.HIGH_FG,
    "MEDIUM": ColorTokens.MEDIUM_FG,
    "LOW": ColorTokens.LOW_FG,
}

STATUS_COLORS: dict[str, str] = {
    "CONFIRMED": ColorTokens.LOW_FG,
    "DISMISSED": ColorTokens.TEXT_MUTED,
    "PENDING_REVIEW": ColorTokens.INFO_FG,
    "ANNOTATED": "#B794F4",
}

TIER_COLORS: dict[str, str] = {
    "CONFIRMED_OBSERVATION": ColorTokens.LOW_FG,
    "DETECTED_INCONSISTENCY": ColorTokens.HIGH_FG,
    "SUSPECTED_MANIPULATION": ColorTokens.CRITICAL_FG,
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
        return SEVERITY_COLORS.get(severity.upper(), ColorTokens.TEXT_MUTED)

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """Return hex color code for a review status."""
        return STATUS_COLORS.get(status.upper(), ColorTokens.TEXT_MUTED)

    @classmethod
    def get_tier_color(cls, tier: str) -> str:
        """Return hex color code for an epistemic tier."""
        return TIER_COLORS.get(tier.upper(), ColorTokens.HIGH_FG)

    @classmethod
    def format_badge_html(cls, text: str, bg_color: str, fg_color: str = "#ffffff") -> str:
        """Return styled HTML span badge (preserved for existing caller compatibility)."""
        # If passed an explicit hex color for bg, use a refined pill presentation
        return format_pill_html(
            text=text,
            fg_color=fg_color,
            bg_color=bg_color,
            border_color="rgba(255, 255, 255, 0.12)",
        )

    @classmethod
    def format_severity_pill(cls, severity: str) -> str:
        """Return a modern Linear-style 12% tint pill badge for severity."""
        sev = severity.upper()
        if sev == "CRITICAL":
            return format_pill_html(
                sev, ColorTokens.CRITICAL_FG, ColorTokens.CRITICAL_BG, ColorTokens.CRITICAL_BORDER
            )
        if sev == "HIGH":
            return format_pill_html(
                sev, ColorTokens.HIGH_FG, ColorTokens.HIGH_BG, ColorTokens.HIGH_BORDER
            )
        if sev == "MEDIUM":
            return format_pill_html(
                sev, ColorTokens.MEDIUM_FG, ColorTokens.MEDIUM_BG, ColorTokens.MEDIUM_BORDER
            )
        return format_pill_html(sev, ColorTokens.LOW_FG, ColorTokens.LOW_BG, ColorTokens.LOW_BORDER)

    @classmethod
    def format_tier_pill(cls, tier: str) -> str:
        """Return a modern 12% tint pill badge for epistemic tiers."""
        t = tier.upper()
        display = t.replace("_", " ")
        if "MANIPULATION" in t:
            return format_pill_html(
                display,
                ColorTokens.CRITICAL_FG,
                ColorTokens.CRITICAL_BG,
                ColorTokens.CRITICAL_BORDER,
            )
        if "INCONSISTENCY" in t:
            return format_pill_html(
                display,
                ColorTokens.HIGH_FG,
                ColorTokens.HIGH_BG,
                ColorTokens.HIGH_BORDER,
            )
        return format_pill_html(
            display,
            ColorTokens.LOW_FG,
            ColorTokens.LOW_BG,
            ColorTokens.LOW_BORDER,
        )

    @classmethod
    def format_status_pill(cls, status: str) -> str:
        """Return a modern 12% tint pill badge for review status."""
        st = status.upper()
        display = st.replace("_", " ")
        if st == "CONFIRMED":
            return format_pill_html(
                display, ColorTokens.LOW_FG, ColorTokens.LOW_BG, ColorTokens.LOW_BORDER
            )
        if st == "DISMISSED":
            return format_pill_html(
                display,
                ColorTokens.TEXT_MUTED,
                "rgba(107, 117, 135, 0.12)",
                "rgba(107, 117, 135, 0.25)",
            )
        if st == "PENDING_REVIEW":
            return format_pill_html(
                display, ColorTokens.INFO_FG, ColorTokens.INFO_BG, ColorTokens.INFO_BORDER
            )
        return format_pill_html(
            display, "#B794F4", "rgba(183, 148, 244, 0.12)", "rgba(183, 148, 244, 0.3)"
        )
