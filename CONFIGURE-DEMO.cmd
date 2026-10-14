@echo off
cd /d "%~dp0"
start "mjPROConnect private setup" ".venv\Scripts\pythonw.exe" setup_demo.py
