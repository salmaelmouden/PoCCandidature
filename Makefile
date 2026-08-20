# Growth Intelligence AI
.PHONY: help install up down status logs migrate seed ingest-youtube dashboard api test lint report n8n-import

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
ALEMBIC := $(VENV)/bin/alembic
STREAMLIT := $(VENV)/bin/streamlit
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

help:
	@echo "Docker stack (recommended):"
	@echo "  make install     - once: create .venv + deps (needed by containers)"
	@echo "  make up          - postgres, migrate, seed, api, dashboard, n8n"
	@echo "  make status      - docker compose ps -a"
	@echo "  make logs        - follow container logs"
	@echo "  make down        - stop stack"
	@echo "  make n8n-import  - import weekly workflow into running n8n"
	@echo "  make report      - local CLI weekly markdown report"
	@echo ""
	@echo "URLs: dashboard :8501 | api :8000/docs | n8n visual :5678"

install:
	@test -d $(VENV) || python3 -m venv $(VENV) || (command -v uv >/dev/null && uv venv $(VENV) --python python3)
	@if command -v uv >/dev/null 2>&1; then \
		UV_SYSTEM_CERTS=1 uv pip install --system-certs -e ".[dev]" || uv pip install --system-certs -e ".[dev]"; \
	else \
		$(PIP) install -U pip && $(PIP) install -e ".[dev]"; \
	fi

up: $(VENV)/bin/python
	docker compose up -d --pull missing
	@echo ""
	@echo "Stack starting. Check: make status"
	@echo "Dashboard: http://localhost:8501"
	@echo "API docs:  http://localhost:8000/docs"
	@echo "n8n UI:    http://localhost:5678  (visual editor)"

$(VENV)/bin/python:
	$(MAKE) install

down:
	docker compose down

status:
	docker compose ps -a

logs:
	docker compose logs -f --tail=100

migrate:
	$(ALEMBIC) upgrade head

seed:
	$(PYTHON) scripts/seed_synthetic_data.py

ingest-youtube:
	@echo "Requires YOUTUBE_API_KEY in .env — see docs/guides/youtube-demo-ingest.md"
	$(PYTHON) scripts/ingest_youtube.py

dashboard:
	$(STREAMLIT) run dashboard/Home.py --server.headless true

api:
	$(UVICORN) app.api.main:app --reload --host 0.0.0.0 --port 8000

report:
	$(PYTHON) scripts/generate_weekly_report.py --days 7

n8n-import:
	docker compose exec n8n n8n import:workflow --input=/import/weekly_growth_report.json
	@echo "Imported. Open http://localhost:5678 and refresh Workflows."

test:
	$(PYTEST) -q

lint:
	$(RUFF) check app tests scripts dashboard
