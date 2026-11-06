"""VeriTrace UI Theme Manager.

Provides helpers to locate, read, and apply QSS stylesheets to
PySide6 QApplication and top-level QWidget hierarchies.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("veritrace.gui.styles.theme_manager")

CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_QSS_PATH = CURRENT_DIR / "dark_theme.qss"


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

