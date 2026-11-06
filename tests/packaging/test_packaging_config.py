"""Unit and Configuration Tests for VeriTrace Desktop Packaging (Milestone 12).

Validates PyInstaller spec definitions, Inno Setup compiler configuration,
Windows application icons, QSS theme stylesheets, and packaging automation.
"""

from __future__ import annotations

import ast
from pathlib import Path

from PIL import Image

from veritrace.gui.app import VeriTraceApp
from veritrace.gui.styles.theme_manager import get_theme_path, load_stylesheet

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PACKAGING_DIR = ROOT_DIR / "packaging"
SPEC_FILE = PACKAGING_DIR / "pyinstaller" / "veritrace.spec"
ISS_FILE = PACKAGING_DIR / "installer" / "veritrace_setup.iss"
ICON_FILE = PACKAGING_DIR / "resources" / "veritrace.ico"
THEME_FILE = ROOT_DIR / "src" / "veritrace" / "gui" / "styles" / "dark_theme.qss"


def test_spec_file_syntax_and_structure() -> None:
    """Verify PyInstaller .spec file syntax and required directives."""
    assert SPEC_FILE.is_file(), f"Spec file not found at {SPEC_FILE}"

    content = SPEC_FILE.read_text(encoding="utf-8")
    # Verify Python syntax
    parsed = ast.parse(content, filename=str(SPEC_FILE))
    assert parsed is not None

    # Check key hidden imports
    mandatory_hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "fitz",
        "pytesseract",
        "cv2",
        "PIL",
        "numpy",
        "rapidfuzz",
        "reportlab",
        "reportlab.platypus",
        "reportlab.pdfgen",
        "sqlalchemy",
        "pydantic",
        "veritrace.domain.rules.arithmetic",
        "veritrace.domain.rules.chronology",
        "veritrace.capabilities.reasoning.contextual_engine",
        "veritrace.capabilities.reporting.dossier_compiler",
        "veritrace.capabilities.forensics.signatures.detector",
        "veritrace.capabilities.forensics.signatures.verifier",
        "veritrace.capabilities.forensics.ela",
    ]
    for imp in mandatory_hidden_imports:
        assert imp in content, f"Mandatory hidden import '{imp}' missing from spec file"

    # Check icon and data directives
    assert "veritrace.ico" in content
    assert "collect_data_files" in content


def test_inno_setup_script_structure() -> None:
    """Verify Inno Setup .iss script configuration and properties."""
    assert ISS_FILE.is_file(), f"Inno Setup script not found at {ISS_FILE}"

    content = ISS_FILE.read_text(encoding="utf-8")

    assert '#define MyAppName "VeriTrace"' in content
    assert '#define MyAppExeName "VeriTrace.exe"' in content
    assert "AppId={{9F3B4A2C-5D1E-4F8A-9C2E-7D4F8A1B2C3D}" in content
    assert "ArchitecturesAllowed=x64compatible" in content
    assert "OutputBaseFilename=VeriTrace-Setup" in content
    assert "OutputDir=" in content
    assert "SetupIconFile=" in content


def test_application_icon_validity() -> None:
    """Verify application icon exists and contains expected resolutions."""
    assert ICON_FILE.is_file(), f"Icon file not found at {ICON_FILE}"
    assert ICON_FILE.stat().st_size > 0

    with Image.open(ICON_FILE) as img:
        assert img.format == "ICO"
        # Verify it has valid dimensions
        assert img.size[0] >= 16 and img.size[1] >= 16


def test_dark_theme_qss_loading() -> None:
    """Verify forensic dark theme QSS stylesheet exists and loads cleanly."""
    assert THEME_FILE.is_file(), f"Dark theme stylesheet missing at {THEME_FILE}"

    theme_path = get_theme_path("dark_theme")
    assert theme_path == THEME_FILE

    css = load_stylesheet("dark_theme")
    assert len(css) > 500
    assert "QMainWindow" in css
    assert "#1e1e2e" in css
    assert "QTableView" in css
    assert "QProgressBar" in css
    assert "QPushButton" in css


def test_veritrace_app_theme_integration() -> None:
    """Verify VeriTraceApp loads the dark theme stylesheet into memory."""
    app = VeriTraceApp(["veritrace", "--headless"])
    assert app.theme_stylesheet != ""
    assert "QMainWindow" in app.theme_stylesheet
    exit_code = app.run()
    assert exit_code == 0


def test_preflight_checks_in_build_script() -> None:
    """Verify build_desktop preflight checks report valid environment."""
    from scripts.packaging.build_desktop import run_preflight_checks

    report = run_preflight_checks()
    assert report.python_ok is True
    assert len(report.missing_modules) == 0, f"Missing modules: {report.missing_modules}"
    assert len(report.missing_assets) == 0, f"Missing assets: {report.missing_assets}"
    assert report.is_valid_for_pyinstaller is True
