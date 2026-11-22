@echo off
echo ============================================================
echo   Resetting CivicPilot Demo Environment
echo ============================================================
cd /d %~dp0api
.venv\Scripts\python.exe reset_demo.py
pause
