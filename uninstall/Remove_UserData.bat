@echo off
setlocal

:: ============================================================================
::  SpecGuard — Data Cleanup & Uninstallation Utility
:: ============================================================================

title SpecGuard User Data Removal

set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%..\"
cd /d "%APP_DIR%"

echo ============================================================================
echo   SpecGuard -- Reset / Remove User Data
echo ============================================================================
echo Application Root: %CD%
echo.
echo WARNING: This will permanently delete:
echo   - Local SQLite database (specguard.db)
echo   - Uploaded documents (data\uploads)
echo   - Exported reports (data\reports)
echo   - Runtime logs (data\logs)
echo   - Processing cache (data\cache)
echo.
echo Application binaries and bundled engineering standards will NOT be deleted.
echo ============================================================================
set /p CONFIRM="Are you sure you want to proceed? (Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo Operation cancelled by user. No files were removed.
    pause
    exit /b 0
)

echo.
echo Cleaning user data directories...

if exist "%CD%\data\database" rd /s /q "%CD%\data\database"
if exist "%CD%\data\uploads" rd /s /q "%CD%\data\uploads"
if exist "%CD%\data\reports" rd /s /q "%CD%\data\reports"
if exist "%CD%\data\logs" rd /s /q "%CD%\data\logs"
if exist "%CD%\data\cache" rd /s /q "%CD%\data\cache"
if exist "%CD%\data\specguard.db" del /f /q "%CD%\data\specguard.db"

echo.
echo User data cleanup completed successfully.
echo You can now delete the entire SpecGuard folder if you wish to uninstall completely.
echo ============================================================================
pause
