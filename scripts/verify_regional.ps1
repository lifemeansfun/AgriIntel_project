# AgriIntel Windows Verification Script
# Run from repository root or scripts/ folder.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskRoot = Split-Path -Parent $ScriptDir
Set-Location $TaskRoot

$PythonBin = if (Test-Path "$TaskRoot\.venv\Scripts\python.exe") {
    "$TaskRoot\.venv\Scripts\python.exe"
} else {
    "python"
}

# Ensure Node/npm is on PATH if installed locally
if (Test-Path "C:\Users\ARYAN\nodejs\PFiles64\nodejs") {
    $env:PATH = "C:\Users\ARYAN\nodejs\PFiles64\nodejs;$env:PATH"
}

Write-Host "==> [1/5] Running pytest backend test suite..." -ForegroundColor Cyan
$env:PYTHONPATH = "."
$env:PYTHONDONTWRITEBYTECODE = "1"
& $PythonBin -m pytest -q -p no:cacheprovider tests

Write-Host "==> [2/5] Verifying regional model artifacts & manifest hashes..." -ForegroundColor Cyan
& $PythonBin -m modules.regional.cli verify-artifacts

Write-Host "==> [3/5] Running frontend linter (oxlint)..." -ForegroundColor Cyan
npm --prefix frontend run lint

Write-Host "==> [4/5] Running frontend arithmetic & guard unit tests..." -ForegroundColor Cyan
npm --prefix frontend test

Write-Host "==> [5/5] Building frontend production bundle..." -ForegroundColor Cyan
npm --prefix frontend run build

Write-Host "`nAll verification checks passed successfully!" -ForegroundColor Green
