@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY_CMD=python"
    ) else (
        echo Python not found. Attempting install with winget...
        where winget >nul 2>&1
        if not %errorlevel%==0 (
            echo winget is not available. Install Python 3.11+ manually and rerun this script.
            exit /b 1
        )

        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo Python installation failed.
            exit /b 1
        )

        where py >nul 2>&1
        if %errorlevel%==0 (
            set "PY_CMD=py -3"
        ) else (
            set "PY_CMD=python"
        )
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    call %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        exit /b 1
    )
)

echo Installing dependencies...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

echo Launching bot window...
start "Professor Thaddeus Bot CLI" /D "%~dp0" cmd /k ""%~dp0.venv\Scripts\python.exe" -m thaddeus_bot %*"

exit /b 0
