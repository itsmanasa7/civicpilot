@echo off
echo ============================================================
echo   Starting CivicPilot Services (Windows)
echo ============================================================
echo.
echo [1/3] Starting PM-KISAN Mirror Portal on http://localhost:4000 ...
start "CivicPilot Mirror (Port 4000)" cmd /k "cd /d %~dp0api && .venv\Scripts\python.exe mirror_server.py 4000"

echo [2/3] Starting FastAPI Backend on http://localhost:8000 ...
start "CivicPilot API (Port 8000)" cmd /k "cd /d %~dp0api && .venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

echo [3/3] Starting Next.js Web UI on http://localhost:3000 ...
start "CivicPilot Web (Port 3000)" cmd /k "cd /d %~dp0web && npm run dev"

echo.
echo All 3 services are launching in separate windows!
echo - Web UI:  http://localhost:3000
echo - API:     http://localhost:8000 (Docs: http://localhost:8000/docs)
echo - Mirror:  http://localhost:4000
echo.
