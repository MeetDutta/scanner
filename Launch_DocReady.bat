@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::  DocReady — Offline Intranet Platform for Template-Aware Formatting & Readiness
::  Windows Portable Launcher Wrapper
:: ============================================================================

title DocReady Portable Launcher

:: Detect installation directory (handles spaces and arbitrary paths)
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo ============================================================================
echo   DocReady -- Document Formatting and Readiness Verification Platform
echo                 100%% Offline Intranet Portable Windows Edition
echo ============================================================================
echo Installation Directory: %APP_DIR%
echo.

:: 1. Check for primary executable (DocReady.exe or SpecGuard.exe)
if exist "%APP_DIR%DocReady.exe" (
    echo Starting DocReady Portable Engine...
    "%APP_DIR%DocReady.exe" %*
    set "EXIT_CODE=!ERRORLEVEL!"
) else if exist "%APP_DIR%SpecGuard.exe" (
    echo Starting DocReady Portable Engine via SpecGuard binary...
    "%APP_DIR%SpecGuard.exe" %*
    set "EXIT_CODE=!ERRORLEVEL!"
) else if exist "%APP_DIR%_internal\DocReady.exe" (
    echo Starting DocReady from internal directory...
    "%APP_DIR%_internal\DocReady.exe" %*
    set "EXIT_CODE=!ERRORLEVEL!"
) else if exist "%APP_DIR%_internal\SpecGuard.exe" (
    echo Starting from internal directory...
    "%APP_DIR%_internal\SpecGuard.exe" %*
    set "EXIT_CODE=!ERRORLEVEL!"
) else (
    echo [ERROR] DocReady.exe could not be found in this directory.
    echo Please make sure you extracted all files from the ZIP archive completely.
    echo.
    set "EXIT_CODE=1"
)

:: 2. If exit was abnormal, pause to let user inspect errors
if not "%EXIT_CODE%"=="0" (
    echo.
    echo ============================================================================
    echo   Application terminated with exit code: %EXIT_CODE%
    echo ============================================================================
    echo Please check the runtime log file for detailed diagnostic details:
    echo   %APP_DIR%data\logs\docready.log
    echo.
    echo For assistance, review TROUBLESHOOTING.md.
    echo ============================================================================
    echo Press any key to close this window...
    pause >nul
)

exit /b %EXIT_CODE%
