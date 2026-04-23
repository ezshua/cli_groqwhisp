@echo off
:: Переходим в папку с проектом (необязательно, если файл уже там)
:: cd /d c:\alexx\Src\cli_groqwhisp
@REM cd /d "%~dp0"

:: Запуск через прямой путь к python.exe внутри venv
:: Если ваша папка окружения называется venv:
start /b "" ".\venv\Scripts\python.exe" main.py

@REM pause
exit
