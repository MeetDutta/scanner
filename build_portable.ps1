# ============================================================================
#  SpecGuard — Automated Windows Portable Build Script (PowerShell)
#  Generates fully self-contained zero-install ZIP package
# ============================================================================

[CmdletBinding()]
param(
    [switch]$SkipTests = $false,
    [switch]$NoZip = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "   SpecGuard -- Automated Windows Portable Package Builder (PowerShell)    " -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Root Workspace: $ScriptDir`n"

# 1. Verify Python
Write-Host "[1/6] Verifying Python Environment..." -ForegroundColor Yellow
try {
    $pyVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    Write-Host "  Detected Python version: $pyVersion" -ForegroundColor Green
    & python -c "import sys; assert sys.version_info >= (3, 9), 'Python 3.9+ required'"
} catch {
    Write-Error "[CRITICAL] Python 3.9+ 64-bit is required in PATH."
    exit 1
}

# 2. Clean Previous Artifacts
Write-Host "`n[2/6] Cleaning Previous Build Artifacts..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Write-Host "  Previous build directories cleaned." -ForegroundColor Green

# 3. Ensure Build Dependencies
Write-Host "`n[3/6] Verifying Build Dependencies..." -ForegroundColor Yellow
try {
    & python -m pip install -q -r requirements-build.txt
    Write-Host "  Build requirements verified." -ForegroundColor Green
} catch {
    Write-Warning "Could not update build requirements automatically. Proceeding with existing packages..."
}

# 4. Run Automated Test Validation
if (-not $SkipTests) {
    Write-Host "`n[4/6] Executing Pre-Build Verification Test Suite..." -ForegroundColor Yellow
    & python -m pytest tests/ -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[CRITICAL] Automated tests failed! Build aborted to prevent publishing broken release."
        exit 1
    }
    Write-Host "  All automated tests passed successfully." -ForegroundColor Green
} else {
    Write-Warning "Pre-build automated tests were skipped (-SkipTests)."
}

# 5. Execute PyInstaller
Write-Host "`n[5/6] Building PyInstaller onedir distribution..." -ForegroundColor Yellow
& pyinstaller --clean -y SpecGuard.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "[CRITICAL] PyInstaller compilation failed."
    exit 1
}

$ExePath = Join-Path $ScriptDir "dist\SpecGuard\SpecGuard.exe"
if (-not (Test-Path $ExePath)) {
    Write-Error "[CRITICAL] SpecGuard.exe was not created at expected path: $ExePath"
    exit 1
}
Write-Host "  SpecGuard.exe built successfully." -ForegroundColor Green

# 6. Assemble Portable Package & ZIP
if (-not $NoZip) {
    Write-Host "`n[6/6] Assembling Portable Layout & Checksummed ZIP Archive..." -ForegroundColor Yellow
    & python package_zip.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[CRITICAL] Portable ZIP generation failed."
        exit 1
    }
}

Write-Host "`n============================================================================" -ForegroundColor Green
Write-Host "   BUILD COMPLETED SUCCESSFULLY!                                            " -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "Output Directory: $(Join-Path $ScriptDir 'dist')`n"
