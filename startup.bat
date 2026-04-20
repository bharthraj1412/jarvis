@echo off
title JARVIS MK37
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

:: Check Python is available
python --version >nul 2>&1
if "%ERRORLEVEL%" NEQ "0" (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Silent mode (auto-startup) - launch voice assistant directly, no menu
if "%~1"=="--silent" (
    echo [JARVIS] Auto-startup - launching voice assistant...
    python start.py voice
    goto :end
)

:: If a mode argument was passed, use it directly
if "%~1" NEQ "" (
    python start.py %1
    goto :end
)

:: Interactive mode - show the launcher menu
echo.
echo ========================================
echo   J.A.R.V.I.S  MARK XXXVII  LAUNCHER
echo ========================================
echo.
python start.py

:end
:: Keep window open if it crashes
if "%ERRORLEVEL%" NEQ "0" (
    echo.
    echo [ERROR] JARVIS MK37 exited with code %ERRORLEVEL%
    echo Press any key to close...
    pause >nul
)
