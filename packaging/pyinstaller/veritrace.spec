# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# VeriTrace Desktop - PyInstaller Build Specification
# Target: Windows 10/11 x64 Standalone Bundle
# ============================================================

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base directory (project root)
base_dir = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
src_dir = os.path.join(base_dir, "src")

# Collect veritrace package data files
datas = []
datas += collect_data_files('veritrace')

# Hidden imports for dynamic capabilities and engines
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'fitz',
    'pytesseract',
    'cv2',
    'PIL',
    'numpy',
    'rapidfuzz',
    'reportlab',
    'sqlalchemy.dialects.sqlite',
]

a = Analysis(
    [os.path.join(src_dir, 'veritrace', 'main.py')],
    pathex=[src_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
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
    name='VeriTrace',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='VeriTrace',
)
