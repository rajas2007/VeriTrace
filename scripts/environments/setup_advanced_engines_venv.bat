@echo off
rem ==============================================================================
rem VeriTrace — Automated Setup for Isolated Advanced Engines Virtual Environment
rem ==============================================================================

setlocal enabledelayedexpansion
set TARGET_DIR=.venv-advanced-engines

echo =================================================================
echo  VeriTrace: Advanced Engines Isolated Sidecar Environment Setup
echo =================================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 is required and must be in PATH.
    exit /b 1
)

if not exist "%TARGET_DIR%" (
    echo [*] Creating isolated virtual environment at %TARGET_DIR%...
    python -m venv "%TARGET_DIR%"
) else (
    echo [+] Existing environment found at %TARGET_DIR%.
)

set PIP_EXE=%TARGET_DIR%\Scripts\pip.exe
set PYTHON_EXE=%TARGET_DIR%\Scripts\python.exe

echo [*] Upgrading pip...
"%PIP_EXE%" install --upgrade pip setuptools wheel

echo [*] Installing advanced engines from requirements-advanced-engines.txt...
"%PIP_EXE%" install -r "%~dp0requirements-advanced-engines.txt"

echo [*] Verifying engine installations...
"%PYTHON_EXE%" -c "import paddleocr; print('PaddleOCR: INSTALLED v' + paddleocr.__version__)"
"%PYTHON_EXE%" -c "import docling; print('Docling: INSTALLED v' + docling.__version__)"

echo =================================================================
echo  Setup Complete! Primary VeriTrace environment (.venv) is untouched.
echo  Sidecar Python: %PYTHON_EXE%
echo =================================================================
endlocal
