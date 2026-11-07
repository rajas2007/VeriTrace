# ==============================================================================
# VeriTrace — Automated Setup for Isolated Advanced Engines Virtual Environment
# ==============================================================================
# Creates an isolated Python virtual environment at '.venv-advanced-engines'
# to host PaddleOCR and IBM Docling without destabilizing primary dependencies.
# ==============================================================================

[CmdletBinding()]
param(
    [string]$TargetDir = ".venv-advanced-engines",
    [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " VeriTrace: Advanced Engines Isolated Sidecar Environment Setup" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check Python 3.11 availability
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
    Write-Error "Python executable not found in PATH. Python 3.11 is required."
    exit 1
}

$pyVer = & python --version
Write-Host "[+] Detected host Python: $pyVer" -ForegroundColor Green

# 2. Check disk space (~3.5 GB required for PyTorch CPU + PaddlePaddle)
$currentDrive = (Get-Item .).Root.Name
$driveInfo = Get-PSDrive ($currentDrive.TrimEnd(":\"))
$freeGb = [math]::Round($driveInfo.Free / 1GB, 2)
Write-Host "[+] Free disk space on drive ${currentDrive}: $freeGb GB (approx 3.5 GB required)" -ForegroundColor Green

if ($freeGb -lt 4.0) {
    Write-Warning "Disk space is under 4 GB. Installation may fail if drive fills up."
}

# 3. Create Virtual Environment
if ($ForceRecreate -and (Test-Path $TargetDir)) {
    Write-Host "[*] Removing existing environment at $TargetDir..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $TargetDir
}

if (-not (Test-Path $TargetDir)) {
    Write-Host "[*] Creating isolated virtual environment at $TargetDir..." -ForegroundColor Cyan
    & python -m venv $TargetDir
} else {
    Write-Host "[+] Existing environment found at $TargetDir." -ForegroundColor Green
}

$pipExe = Join-Path $TargetDir "Scripts\pip.exe"
$pyVenvExe = Join-Path $TargetDir "Scripts\python.exe"

if (-not (Test-Path $pipExe)) {
    Write-Error "Virtual environment creation failed; pip not found at $pipExe."
    exit 1
}

# 4. Upgrade pip and build tools
Write-Host "[*] Upgrading pip and wheel in isolated environment..." -ForegroundColor Cyan
& $pipExe install --upgrade pip setuptools wheel

# 5. Install requirements
$reqFile = Join-Path $PSScriptRoot "requirements-advanced-engines.txt"
Write-Host "[*] Installing advanced engines from $reqFile..." -ForegroundColor Cyan
Write-Host "    (Downloading PyTorch CPU, PaddlePaddle CPU, PaddleOCR, and Docling)..." -ForegroundColor Yellow

& $pipExe install -r $reqFile

# 6. Verify installations
Write-Host "[*] Verifying engine installations in isolated environment..." -ForegroundColor Cyan

$verifyScript = @"
import sys
results = []
try:
    import paddleocr
    results.append('PaddleOCR: INSTALLED (v' + getattr(paddleocr, '__version__', 'unknown') + ')')
except Exception as e:
    results.append('PaddleOCR: FAILED (' + str(e) + ')')

try:
    import docling
    results.append('Docling: INSTALLED (v' + getattr(docling, '__version__', 'unknown') + ')')
except Exception as e:
    results.append('Docling: FAILED (' + str(e) + ')')

print('\n'.join(results))
"@

$verifyOutput = & $pyVenvExe -c $verifyScript
Write-Host $verifyOutput -ForegroundColor Green

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Setup Complete! Primary VeriTrace environment (.venv) is untouched." -ForegroundColor Cyan
Write-Host " Sidecar Python path: $pyVenvExe" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
