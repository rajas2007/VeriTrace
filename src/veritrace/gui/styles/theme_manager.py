"""Theme and styling manager for VeriTrace desktop interface."""

from __future__ import annotations

from pathlib import Path

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


class ThemeManager:
    """Manages Qt dark theme stylesheet loading and badge formatting."""

    _stylesheet: str | None = None

    @classmethod
    def get_stylesheet(cls) -> str:
        """Load and return the QSS dark theme stylesheet."""
        if cls._stylesheet is None:
            qss_path = Path(__file__).parent / "dark_theme.qss"
            if qss_path.exists():
                cls._stylesheet = qss_path.read_text(encoding="utf-8")
            else:
                cls._stylesheet = ""
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
