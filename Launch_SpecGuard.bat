@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::  SpecGuard — Autonomous Engineering Document Quality & Standards Framework
::  Windows Portable Launcher Wrapper
:: ============================================================================

title SpecGuard Portable Launcher

:: Detect installation directory (handles spaces and arbitrary paths)
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo ============================================================================
echo   SpecGuard -- Engineering Document Quality and Standards System
echo                 100%% Offline Portable Windows Edition
echo ============================================================================
echo Installation Directory: %APP_DIR%
echo.

:: 1. Check for primary executable
if exist "%APP_DIR%SpecGuard.exe" (
    echo Starting SpecGuard Portable Engine...
    "%APP_DIR%SpecGuard.exe" %*
    set "EXIT_CODE=!ERRORLEVEL!"
) else if exist "%APP_DIR%_internal\SpecGuard.exe" (
    echo Starting SpecGuard from internal directory...
    "%APP_DIR%_internal\SpecGuard.exe" %*
    set "EXIT_CODE=!ERRORLEVEL!"
) else (
    echo [ERROR] SpecGuard.exe could not be found in this directory.
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
    echo   %APP_DIR%data\logs\specguard.log
    echo.
    echo For assistance, review TROUBLESHOOTING.md.
    echo ============================================================================
    echo Press any key to close this window...
    pause >nul
)

exit /b %EXIT_CODE%
