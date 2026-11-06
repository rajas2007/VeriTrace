#!/usr/bin/env python3
"""VeriTrace Desktop Packaging and Release Automation Script.

Orchestrates pre-flight environment checks, PyInstaller standalone executable
compilation, and optional Inno Setup Windows installer generation.

Usage:
    python scripts/packaging/build_desktop.py --check-only
    python scripts/packaging/build_desktop.py --clean --skip-installer
    python scripts/packaging/build_desktop.py --all
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_desktop")

# Project Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PACKAGING_DIR = ROOT_DIR / "packaging"
SPEC_FILE = PACKAGING_DIR / "pyinstaller" / "veritrace.spec"
ISS_FILE = PACKAGING_DIR / "installer" / "veritrace_setup.iss"
ICON_FILE = PACKAGING_DIR / "resources" / "veritrace.ico"
THEME_FILE = ROOT_DIR / "src" / "veritrace" / "gui" / "styles" / "dark_theme.qss"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
EXE_TARGET = DIST_DIR / "VeriTrace" / "VeriTrace.exe"
INSTALLER_TARGET = DIST_DIR / "installer" / "VeriTrace-Setup.exe"

# Required dependencies for complete standalone build
REQUIRED_MODULES = [
    "PySide6",
    "fitz",
    "cv2",
    "PIL",
    "numpy",
    "rapidfuzz",
    "reportlab",
    "sqlalchemy",
    "pydantic",
    "PyInstaller",
]


@dataclass
class PreflightReport:
    """Encapsulates results of pre-flight environment checks."""

    python_ok: bool
    python_version: str
    missing_modules: list[str] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    iscc_path: Path | None = None

    @property
    def is_valid_for_pyinstaller(self) -> bool:
        """Return True if environment satisfies all PyInstaller requirements."""
        return self.python_ok and len(self.missing_modules) == 0 and len(self.missing_assets) == 0


def find_inno_setup_compiler() -> Path | None:
    """Search for Inno Setup compiler (ISCC.exe) on the system.

    Returns:
        Path to ISCC.exe if found, else None.
    """
    # 1. Check system PATH
    which_iscc = shutil.which("iscc") or shutil.which("iscc.exe")
    if which_iscc:
        return Path(which_iscc)

    # 2. Check standard Windows installation directories
    candidate_dirs = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Inno Setup 6",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Inno Setup 6",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Inno Setup 5",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Inno Setup 5",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6",
    ]

    for candidate in candidate_dirs:
        exe = candidate / "ISCC.exe"
        if exe.is_file():
            return exe

    return None


def run_preflight_checks() -> PreflightReport:
    """Execute pre-flight checks on runtime, modules, assets, and tools.

    Returns:
        PreflightReport with validation results.
    """
    logger.info("Executing VeriTrace desktop pre-flight validation...")

    # 1. Python version check
    v = sys.version_info
    py_ver_str = f"{v.major}.{v.minor}.{v.micro}"
    python_ok = v.major == 3 and v.minor >= 11
    if python_ok:
        logger.info("  ✓ Python runtime: %s (satisfies >= 3.11)", py_ver_str)
    else:
        logger.error("  ✗ Python runtime: %s (requires >= 3.11)", py_ver_str)

    # 2. Required modules
    missing_modules: list[str] = []
    for mod in REQUIRED_MODULES:
        spec = importlib.util.find_spec(mod)
        if spec is not None:
            logger.info("  ✓ Module %s: Available", mod)
        else:
            logger.warning("  ✗ Module %s: NOT FOUND", mod)
            missing_modules.append(mod)

    # 3. Required assets and files
    missing_assets: list[str] = []
    asset_checks = [
        ("Spec file", SPEC_FILE),
        ("Inno Setup script", ISS_FILE),
        ("Application icon", ICON_FILE),
        ("Dark theme QSS", THEME_FILE),
    ]
    for name, path in asset_checks:
        if path.is_file():
            logger.info("  ✓ Asset %s: %s (exists)", name, path.name)
        else:
            logger.warning("  ✗ Asset %s: %s (MISSING)", name, path)
            missing_assets.append(str(path))

    # 4. Inno Setup compiler
    iscc_path = find_inno_setup_compiler()
    if iscc_path:
        logger.info("  ✓ Inno Setup Compiler: %s", iscc_path)
    else:
        logger.info("  ℹ Inno Setup Compiler (ISCC.exe): Not installed on host.")

    report = PreflightReport(
        python_ok=python_ok,
        python_version=py_ver_str,
        missing_modules=missing_modules,
        missing_assets=missing_assets,
        iscc_path=iscc_path,
    )
    return report


def clean_build_artifacts() -> None:
    """Remove previous build and dist directories."""
    logger.info("Cleaning previous packaging artifacts...")
    for target in [DIST_DIR, BUILD_DIR]:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            logger.info("  ✓ Removed: %s", target)


def build_pyinstaller_bundle() -> bool:
    """Invoke PyInstaller using packaging/pyinstaller/veritrace.spec.

    Returns:
        True if build succeeded and VeriTrace.exe exists.
    """
    logger.info("Invoking PyInstaller build for VeriTrace desktop...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        str(SPEC_FILE),
    ]

    logger.info("Command: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=False)

    if result.returncode != 0:
        logger.error("PyInstaller compilation failed with code %d", result.returncode)
        return False

    if not EXE_TARGET.is_file():
        logger.error("Expected executable not found at: %s", EXE_TARGET)
        return False

    exe_size_mb = EXE_TARGET.stat().st_size / (1024 * 1024)
    logger.info("✓ PyInstaller bundle created successfully: %s (%.2f MB)", EXE_TARGET, exe_size_mb)
    return True


def build_inno_setup_installer(iscc_path: Path) -> bool:
    """Compile the Inno Setup installer script.

    Args:
        iscc_path: Path to ISCC.exe executable.

    Returns:
        True if installer was compiled successfully.
    """
    logger.info("Compiling Windows installer with Inno Setup...")
    installer_dir = DIST_DIR / "installer"
    installer_dir.mkdir(parents=True, exist_ok=True)

    cmd = [str(iscc_path), str(ISS_FILE)]
    logger.info("Command: %s", " ".join(cmd))

    result = subprocess.run(cmd, cwd=str(PACKAGING_DIR / "installer"), capture_output=False)
    if result.returncode != 0:
        logger.error("Inno Setup compilation failed with code %d", result.returncode)
        return False

    if not INSTALLER_TARGET.is_file():
        logger.warning(
            "Expected installer at %s not found. Checking %s",
            INSTALLER_TARGET,
            installer_dir,
        )
        return False

    installer_size_mb = INSTALLER_TARGET.stat().st_size / (1024 * 1024)
    logger.info("✓ Windows installer compiled: %s (%.2f MB)", INSTALLER_TARGET, installer_size_mb)
    return True


def main() -> int:
    """Command line entry point for desktop packaging automation."""
    parser = argparse.ArgumentParser(
        description="VeriTrace Desktop Packaging and Release Automation"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run pre-flight checks and validate packaging configuration without building.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build/ and dist/ directories before running build.",
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Build PyInstaller bundle only; skip Inno Setup compilation.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full end-to-end release pipeline (pre-flight, PyInstaller, Inno Setup).",
    )
    args = parser.parse_args()

    report = run_preflight_checks()

    if args.check_only:
        if report.is_valid_for_pyinstaller:
            logger.info("★ Pre-flight check PASSED: Environment is ready for packaging.")
            return 0
        logger.error("✗ Pre-flight check FAILED: Missing required modules or assets.")
        return 1

    if not report.is_valid_for_pyinstaller:
        logger.error(
            "Cannot proceed: pre-flight checks failed. Run with --check-only to see details."
        )
        return 1

    if args.clean:
        clean_build_artifacts()

    # 1. Build PyInstaller bundle
    success = build_pyinstaller_bundle()
    if not success:
        return 1

    # 2. Build Inno Setup installer if requested and available
    if not args.skip_installer:
        if report.iscc_path:
            installer_success = build_inno_setup_installer(report.iscc_path)
            if not installer_success:
                logger.error("Installer build failed.")
                return 1
        else:
            logger.info(
                "ℹ Skipping installer build: Inno Setup (ISCC.exe) is not installed.\n"
                "  To compile VeriTrace-Setup.exe, install Inno Setup 6 from:\n"
                "  https://jrsoftware.org/isdl.php"
            )

    logger.info("★ Desktop packaging workflow completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

