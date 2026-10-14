@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 setup_local.py
) else (
    python setup_local.py
)
pause
