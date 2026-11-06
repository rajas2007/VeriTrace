# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# VeriTrace Desktop - PyInstaller Build Specification
# Target: Windows 10/11 x64 Standalone Bundle
# ============================================================

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base directory (project root)
base_dir = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
src_dir = os.path.join(base_dir, "src")
resources_dir = os.path.join(base_dir, "packaging", "resources")

# Application icon
app_icon = os.path.join(resources_dir, "veritrace.ico")
if not os.path.isfile(app_icon):
    app_icon = None

# Collect package data files and assets
datas = []
datas += collect_data_files("veritrace")

# Include alembic.ini if present in root
alembic_ini = os.path.join(base_dir, "alembic.ini")
if os.path.isfile(alembic_ini):
    datas.append((alembic_ini, "."))

# Hidden imports for dynamic engines, plugins, and forensic components
hiddenimports = [
    # PySide6 Qt bindings
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    # Document Ingestion & Rasterization
    "fitz",
    "pymupdf",
    # Scanned Document OCR
    "pytesseract",
    # Computer Vision & Forensics
    "cv2",
    "PIL",
    "PIL.Image",
    "PIL.ImageChops",
    "PIL.ImageEnhance",
    "numpy",
    "rapidfuzz",
    # Auditor-Grade PDF Dossier Compilation
    "reportlab",
    "reportlab.platypus",
    "reportlab.platypus.flowables",
    "reportlab.platypus.paragraph",
    "reportlab.platypus.tables",
    "reportlab.lib",
    "reportlab.lib.colors",
    "reportlab.lib.pagesizes",
    "reportlab.lib.units",
    "reportlab.lib.styles",
    "reportlab.pdfgen",
    "reportlab.pdfgen.canvas",
    # SQLite WAL Persistence & Models
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.orm",
    # Pydantic Settings
    "pydantic",
    "pydantic_settings",
    # VeriTrace Domain Rules & Reasoning
    "veritrace.domain.rules.arithmetic",
    "veritrace.domain.rules.chronology",
    "veritrace.capabilities.reasoning.contextual_engine",
    "veritrace.capabilities.reasoning.synthesizer",
    # VeriTrace Dossier Reporting
    "veritrace.capabilities.reporting.dossier_compiler",
    "veritrace.capabilities.reporting.pdf_builder",
    "veritrace.capabilities.reporting.json_builder",
    "veritrace.capabilities.reporting.models",
    # VeriTrace Forensic Engines
    "veritrace.capabilities.forensics.signatures.detector",
    "veritrace.capabilities.forensics.signatures.stroke_analyzer",
    "veritrace.capabilities.forensics.signatures.verifier",
    "veritrace.capabilities.forensics.ela",
    "veritrace.capabilities.forensics.font_baseline",
    "veritrace.capabilities.forensics.clone_detection",
    "veritrace.capabilities.forensics.evidence_cropper",
    # VeriTrace Extraction & Quality Engines
    "veritrace.capabilities.extraction.rasterizer",
    "veritrace.capabilities.extraction.ocr_engine",
    "veritrace.capabilities.extraction.table_extractor",
    "veritrace.capabilities.quality.scoring",
    "veritrace.gui.styles.theme_manager",
]

# Exclude unnecessary heavyweight modules
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "IPython",
    "notebook",
    "pytest",
]

a = Analysis(
    [os.path.join(src_dir, "veritrace", "main.py")],
    pathex=[src_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VeriTrace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=app_icon,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VeriTrace",
)
