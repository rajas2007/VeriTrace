"""Application Bootstrap and Early Environment Initialization.

Configures structured logging, verifies environment variables, prepares
local %LOCALAPPDATA%/VeriTrace directories, and establishes Qt High-DPI attributes.

Execution scheduled for Milestone 0.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("veritrace.bootstrap")


def setup_logging(log_level: int = logging.INFO) -> None:
    """Configure structured logging for desktop runtime."""
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def resolve_data_directory() -> Path:
    """Resolve the local workstation data directory (%LOCALAPPDATA%/VeriTrace)."""
    base = os.environ.get("VERITRACE_DATA_DIR")
    if base:
        data_dir = Path(base)
    elif sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        data_dir = Path(local_app_data) / "VeriTrace"
    else:
        data_dir = Path.home() / ".veritrace"
    return data_dir


def bootstrap_application() -> None:
    """Perform early application bootstrap before Qt initialization."""
    setup_logging()
    data_dir = resolve_data_directory()
    logger.info(f"VeriTrace runtime initialized. Target data dir: {data_dir}")
