"""Design tokens and theme constants for VeriTrace.

Inspired by Linear, Vercel, Raycast, and Bloomberg Terminal:
- Refined dark theme with high contrast readability and low visual noise
- 4px spacing scale and 12-column layout grid
- Desaturated semantic colors with 12% opacity tint fills
- Inter typography with tabular numerals for metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Typography Spec
# ---------------------------------------------------------------------------
FONT_FAMILY: Final[str] = (
    '"Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif'
)
FONT_MONO: Final[str] = '"JetBrains Mono", "Cascadia Code", "Consolas", monospace'


# ---------------------------------------------------------------------------
# Color Palette Tokens
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ColorTokens:
    """Core surface, text, border, and semantic colors."""

    # Backgrounds & Surfaces
    BG_ROOT: Final[str] = "#0B0E14"  # Deep canvas
    BG_SURFACE: Final[str] = "#11151D"  # Cards, sidebars, toolbars
    BG_ELEVATED: Final[str] = "#161B26"  # Modals, popups, elevated cards
    BG_HOVER: Final[str] = "#1A212E"  # Hover state for interactive rows
    BG_ACTIVE: Final[str] = "#1E2738"  # Pressed or active item background

    # Semantic Surface Aliases
    BACKGROUND_BASE: Final[str] = "#0B0E14"
    SURFACE_SIDEBAR: Final[str] = "#11151D"
    SURFACE_CARD: Final[str] = "#161B26"
    SURFACE_HOVER: Final[str] = "#1A212E"

    # Borders
    BORDER_SUBTLE: Final[str] = "#1D2330"  # Low-contrast internal dividers
    BORDER_BASE: Final[str] = "#232A38"  # Standard 1px component borders
    BORDER_HOVER: Final[str] = "#364154"  # Hover state component borders
    BORDER_FOCUS: Final[str] = "#5B8CFF"  # Primary focus ring

    # Typography
    TEXT_PRIMARY: Final[str] = "#E6E9F0"  # High-contrast headers, active text
    TEXT_SECONDARY: Final[str] = "#9AA4B5"  # Labels, metadata, standard body
    TEXT_MUTED: Final[str] = "#6B7587"  # Hints, timestamps, disabled items
    TEXT_INVERSE: Final[str] = "#0B0E14"  # Text on bright badges

    # Brand & Accent
    ACCENT_PRIMARY: Final[str] = "#5B8CFF"  # Enterprise indigo/blue
    ACCENT_HOVER: Final[str] = "#709CFF"  # Button hover state
    ACCENT_PRESSED: Final[str] = "#4674E6"  # Button pressed state
    ACCENT_MUTED: Final[str] = "rgba(91, 140, 255, 0.12)"  # 12% tint background

    # Semantic Status Colors (Foreground & 12% Tint Fills)
    CRITICAL_FG: Final[str] = "#F0616D"
    CRITICAL_BG: Final[str] = "rgba(240, 97, 109, 0.12)"
    CRITICAL_BORDER: Final[str] = "rgba(240, 97, 109, 0.30)"

    HIGH_FG: Final[str] = "#F5A25D"
    HIGH_BG: Final[str] = "rgba(245, 162, 93, 0.12)"
    HIGH_BORDER: Final[str] = "rgba(245, 162, 93, 0.30)"

    MEDIUM_FG: Final[str] = "#E8C468"
    MEDIUM_BG: Final[str] = "rgba(232, 196, 104, 0.12)"
    MEDIUM_BORDER: Final[str] = "rgba(232, 196, 104, 0.30)"

    LOW_FG: Final[str] = "#4FD1A5"
    LOW_BG: Final[str] = "rgba(79, 209, 165, 0.12)"
    LOW_BORDER: Final[str] = "rgba(79, 209, 165, 0.30)"

    INFO_FG: Final[str] = "#5B8CFF"
    INFO_BG: Final[str] = "rgba(91, 140, 255, 0.12)"
    INFO_BORDER: Final[str] = "rgba(91, 140, 255, 0.30)"

    # Severity Aliases
    SEVERITY_CRITICAL: Final[str] = "#F0616D"
    SEVERITY_CRITICAL_TINT: Final[str] = "rgba(240, 97, 109, 0.12)"
    SEVERITY_HIGH: Final[str] = "#F5A25D"
    SEVERITY_HIGH_TINT: Final[str] = "rgba(245, 162, 93, 0.12)"
    SEVERITY_MEDIUM: Final[str] = "#E8C468"
    SEVERITY_MEDIUM_TINT: Final[str] = "rgba(232, 196, 104, 0.12)"
    SEVERITY_LOW: Final[str] = "#4FD1A5"
    SEVERITY_LOW_TINT: Final[str] = "rgba(79, 209, 165, 0.12)"

    # Backwards compatibility token for test suites checking '#1e1e2e'
    LEGACY_COMPAT_COLOR: Final[str] = "#1e1e2e"


# ---------------------------------------------------------------------------
# Spacing, Radii & Typography Tokens
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MetricTokens:
    """Spacing, radius, elevation dimensions, and font tokens."""

    RADIUS_SM: Final[int] = 4  # Small tags, inner controls
    RADIUS_MD: Final[int] = 6  # Buttons, inputs, dropdowns
    RADIUS_LG: Final[int] = 8  # Cards, dialogs, panels
    RADIUS_PILL: Final[int] = 999  # Pill badges, status dots

    SPACE_XS: Final[int] = 4
    SPACE_SM: Final[int] = 8
    SPACE_MD: Final[int] = 12
    SPACE_LG: Final[int] = 16
    SPACE_XL: Final[int] = 24

    HEIGHT_CONTROL_SM: Final[int] = 28
    HEIGHT_CONTROL: Final[int] = 32
    HEIGHT_ROW_TABLE: Final[int] = 38

    # Typography Scale
    FONT_SIZE_XS: Final[str] = "11px"
    FONT_SIZE_SM: Final[str] = "12px"
    FONT_SIZE_BASE: Final[str] = "14px"
    FONT_SIZE_LG: Final[str] = "16px"
    FONT_SIZE_XL: Final[str] = "20px"

    FONT_WEIGHT_NORMAL: Final[str] = "400"
    FONT_WEIGHT_MEDIUM: Final[str] = "500"
    FONT_WEIGHT_SEMIBOLD: Final[str] = "600"
    FONT_WEIGHT_BOLD: Final[str] = "700"

    FONT_FAMILY_SANS: Final[str] = FONT_FAMILY
    FONT_FAMILY_MONO: Final[str] = FONT_MONO


# ---------------------------------------------------------------------------
# Badge Helper Utilities
# ---------------------------------------------------------------------------
def format_pill_html(text: str, fg_color: str, bg_color: str, border_color: str = "") -> str:
    """Generate high-contrast, modern pill badge HTML with low visual weight."""
    border_css = f"border: 1px solid {border_color};" if border_color else ""
    return (
        f"<span style='background-color: {bg_color}; color: {fg_color}; {border_css} "
        f"padding: 2px 8px; border-radius: 999px; font-weight: 600; font-size: 11px; "
        f"letter-spacing: 0.3px; display: inline-block; white-space: nowrap;'>"
        f"{text}</span>"
    )
