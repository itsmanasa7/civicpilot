.PHONY: dev api web mirror bot reset test install install-api install-web help

# Default target
help:
	@echo "CivicPilot Makefile"
	@echo ""
	@echo "  make dev          - Run API + Web + Mirror servers concurrently"
	@echo "  make api          - Run FastAPI backend only (port 8000)"
	@echo "  make web          - Run Next.js frontend only (port 3000)"
	@echo "  make mirror       - Run PM-KISAN Mirror portal (port 4000)"
	@echo "  make bot          - Run Telegram Bot service"
	@echo "  make reset        - One-command clean reset for demo"
	@echo "  make test         - Run full pytest test suite"
	@echo "  make install      - Install all dependencies"
	@echo "  make install-api  - Install Python dependencies"
	@echo "  make install-web  - Install Node dependencies"

# Run all servers (Windows: start processes)
dev:
	@echo "Starting CivicPilot (API on :8000, Web on :3000, Mirror on :4000)..."
	start "CivicPilot Mirror" cmd /k "cd api && .venv\Scripts\python.exe mirror_server.py 4000"
	start "CivicPilot API" cmd /k "cd api && .venv\Scripts\activate && uvicorn main:app --reload --port 8000"
	start "CivicPilot Web" cmd /k "cd web && npm run dev"

# Individual servers
api:
	cd api && .venv\Scripts\activate && uvicorn main:app --reload --port 8000

web:
	cd web && npm run dev

mirror:
	cd api && .venv\Scripts\python.exe mirror_server.py 4000

bot:
	cd api && .venv\Scripts\python.exe -m bot.telegram_bot

reset:
	cd api && .venv\Scripts\python.exe reset_demo.py

# Tests
test:
	cd api && .venv\Scripts\pytest -v

# Installation
install: install-api install-web

install-api:
	cd api && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt && .venv\Scripts\playwright install chromium

install-web:
	cd web && npm install

# Clean
clean:
	cd api && rmdir /s /q .venv 2>NUL || true
	cd web && rmdir /s /q node_modules 2>NUL || true
	cd web && rmdir /s /q .next 2>NUL || true
