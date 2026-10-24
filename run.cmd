@echo off
chcp 65001 >nul
cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python311\python.exe" app.py
