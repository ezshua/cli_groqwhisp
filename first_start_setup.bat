@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

echo.
echo === Groq Whisperer: first-time setup ===
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher "py" not found. Install Python 3.11+ and try again.
    pause
    exit /b 1
)

if not exist ".\venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    py -3.11 -m venv venv >nul 2>nul
    if errorlevel 1 (
        echo [WARN] Python 3.11 not found, trying default Python...
        py -m venv venv
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment.
            pause
            exit /b 1
        )
    )
) else (
    echo [INFO] Existing virtual environment found.
)

call ".\venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo [INFO] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

set "API_KEY_SOURCE=none"
if defined GROQ_API_KEY (
    set "API_KEY_SOURCE=session"
) else (
    for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v GROQ_API_KEY 2^>nul ^| find "GROQ_API_KEY"') do (
        set "GROQ_API_KEY=%%B"
        set "API_KEY_SOURCE=registry"
    )
)

if /i "!API_KEY_SOURCE!"=="none" (
    echo.
    echo [ACTION] Enter your Groq API key (it will be saved to user environment variables):
    set /p GROQ_API_KEY=GROQ_API_KEY=
    if not defined GROQ_API_KEY (
        echo [ERROR] GROQ_API_KEY is empty.
        pause
        exit /b 1
    )
    setx GROQ_API_KEY "!GROQ_API_KEY!" >nul
    echo [INFO] GROQ_API_KEY saved for future sessions.
) else (
    echo [INFO] GROQ_API_KEY found in !API_KEY_SOURCE!.
)

echo.
echo [OK] Setup completed. Starting application...
start /b "" ".\venv\Scripts\python.exe" main.py
echo [INFO] Application started in background.
exit /b 0
