@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo.
echo === Groq Whisperer: build Windows EXE ===
echo.

if not exist ".\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Run first_start_setup.bat first.
    pause
    exit /b 1
)

call ".\venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [INFO] Installing/updating PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

if exist ".\build" (
    echo [INFO] Removing old build folder...
    rmdir /s /q ".\build"
)

if exist ".\dist" (
    echo [INFO] Removing old dist folder...
    rmdir /s /q ".\dist"
)

echo [INFO] Building executable from main.spec...
pyinstaller --clean main.spec
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [OK] Build completed.
echo [OK] Executable path: dist\main.exe
exit /b 0
