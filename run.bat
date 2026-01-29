@echo off
REM ============================================================================
REM Excel to JSON Transformation - Windows Batch Script
REM ============================================================================
REM
REM This script runs the Excel to JSON transformation using the paths
REM configured in config_paths.py
REM
REM Prerequisites:
REM   - Python 3.7+ installed
REM   - pandas and openpyxl packages installed (pip install pandas openpyxl)
REM
REM Usage:
REM   1. Double-click this file, OR
REM   2. Run from command prompt: run.bat
REM
REM ============================================================================

echo ============================================================================
echo Excel to JSON Transformation Framework
echo ============================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and add it to your PATH
    pause
    exit /b 1
)

REM Run the transformation
python main.py

echo.
echo ============================================================================
if errorlevel 1 (
    echo Transformation FAILED
) else (
    echo Transformation COMPLETED SUCCESSFULLY
)
echo ============================================================================
echo.

pause
