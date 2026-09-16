@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::  SpecGuard — Automated Windows Portable Build Script
::  Generates fully self-contained zero-install ZIP package
:: ============================================================================

title SpecGuard Windows Portable Builder
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ============================================================================
echo   SpecGuard -- Automated Windows Portable Package Builder
echo ============================================================================
echo Root Workspace: %ROOT_DIR%
echo.

:: 1. Check Python Availability
where python >nul 2>nul
if not %ERRORLEVEL%==0 (
    echo [ERROR] Python 3.9+ was not found in system PATH.
    echo Please install Python 64-bit and ensure 'python' is accessible.
    pause
    exit /b 1
)

echo [1/7] Verifying Python Environment...
python -c "import sys; assert sys.version_info >= (3, 9), 'Python 3.9+ required'; print('  Python version: ' + sys.version)"
if not %ERRORLEVEL%==0 (
    echo [ERROR] Python verification failed. Python 3.9+ (64-bit) is required.
    pause
    exit /b 1
)

:: 2. Clean Previous Build Artifacts
echo [2/7] Cleaning previous build artifacts...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "*.spec.bak" del /f /q "*.spec.bak"

:: 3. Install Packaging Dependencies
echo [3/7] Verifying build dependencies (PyInstaller)...
python -m pip install -q -r requirements-build.txt
if not %ERRORLEVEL%==0 (
    echo [WARNING] Could not install requirements-build.txt automatically.
    echo Attempting to proceed with existing environment packages...
)

:: 4. Run Automated Test Verification
echo [4/7] Running automated pre-build test validation...
python -m pytest tests/ -q
if not %ERRORLEVEL%==0 (
    echo.
    echo [CRITICAL ERROR] Test suite verification failed!
    echo Refusing to produce a release package from failing code.
    echo Fix the failing tests before packaging.
    pause
    exit /b 1
)
echo   Test suite passed successfully.

:: 5. Execute PyInstaller
echo [5/7] Building PyInstaller onedir distribution (SpecGuard.spec)...
pyinstaller --clean -y SpecGuard.spec
if not %ERRORLEVEL%==0 (
    echo.
    echo [CRITICAL ERROR] PyInstaller build failed!
    echo Inspect the console messages above for compilation errors.
    pause
    exit /b 1
)

:: 6. Verify Executable Generation
if not exist "dist\SpecGuard\SpecGuard.exe" (
    echo [CRITICAL ERROR] dist\SpecGuard\SpecGuard.exe was not created!
    pause
    exit /b 1
)
echo   SpecGuard.exe compiled successfully.

:: 7. Assemble Portable Layout & Generate Checksummed ZIP
echo [6/7] Assembling portable structure and packaging ZIP...
python package_zip.py
if not %ERRORLEVEL%==0 (
    echo.
    echo [CRITICAL ERROR] Portable packaging failed!
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo   BUILD COMPLETED SUCCESSFULLY!
echo ============================================================================
echo Portable package generated in: %ROOT_DIR%dist\
echo Checksum verified. You can now distribute the ZIP archive.
echo ============================================================================
pause
