@echo off
setlocal

REM --- Launcher for the Stock Performance Explorer Streamlit app ---
cd /d "%~dp0"

REM Check whether the existing venv points at a Python that still exists.
set "VENV_OK=0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "VENV_OK=1"
)

if "%VENV_OK%"=="0" (
    echo [launch] No working virtual environment found. Creating a fresh one...
    if exist ".venv" (
        echo [launch] Removing stale .venv ...
        rmdir /s /q ".venv"
    )
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo [launch] Failed to create the virtual environment. Make sure Python 3 is installed.
        pause
        exit /b 1
    )
)

echo [launch] Upgrading pip and installing/updating requirements...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [launch] Failed to install dependencies.
    pause
    exit /b 1
)

echo [launch] Starting Streamlit...
call ".venv\Scripts\python.exe" -m streamlit run app.py

endlocal
