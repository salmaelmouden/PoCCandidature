# Growth Intelligence AI
.PHONY: help install up up-n8n n8n-build down status logs migrate seed ingest-youtube classify public-report dashboard api test eval lint report n8n-import

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
ALEMBIC := $(VENV)/bin/alembic
STREAMLIT := $(VENV)/bin/streamlit
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

# Corporate proxy defaults (override in env if different)
HTTP_PROXY ?= http://fproxy.havre-port.lan:8080
HTTPS_PROXY ?= http://fproxy.havre-port.lan:8080
NO_PROXY ?= localhost,127.0.0.1
CORP_CA ?= $(HOME)/certs/full-bundle.pem
N8N_IMAGE ?= gia-n8n:local

help:
	@echo "Docker stack (recommended):"
	@echo "  make install     - once: create .venv + deps"
	@echo "  make up          - postgres, migrate, seed, api, dashboard"
	@echo "  make n8n-build   - build local n8n image from cached node:20-slim (no Docker Hub n8n)"
	@echo "  make up-n8n      - core + n8n visual UI (:5678)"
	@echo "  make n8n-import  - import weekly workflow into running n8n"
	@echo "  make report      - CLI weekly markdown report"
	@echo "  make eval        - agent evaluation suite (Phase 10)"
	@echo "  make test        - full pytest"
	@echo ""
	@echo "URLs: dashboard :8501 | api :8000/docs | n8n :5678"
	@echo "Demo: docs/guides/demo-script.md"

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
	@echo "Core stack starting. Check: make status"
	@echo "Dashboard: http://localhost:8501"
	@echo "API docs:  http://localhost:8000/docs"
	@echo "n8n UI:    make n8n-build && make up-n8n"

n8n-build:
	@test -f "$(CORP_CA)" || (echo "Missing CA file: $(CORP_CA)"; exit 1)
	@mkdir -p docker/n8n/certs
	cp "$(CORP_CA)" docker/n8n/certs/full-bundle.pem
	@echo "Building $(N8N_IMAGE) from local node:20-slim (npm install n8n)..."
	docker build \
		--build-arg HTTP_PROXY="$(HTTP_PROXY)" \
		--build-arg HTTPS_PROXY="$(HTTPS_PROXY)" \
		--build-arg NO_PROXY="$(NO_PROXY)" \
		-t "$(N8N_IMAGE)" \
		docker/n8n
	@echo "Built $(N8N_IMAGE). Next: make up-n8n"

up-n8n: $(VENV)/bin/python
	@if ! docker image inspect "$(N8N_IMAGE)" >/dev/null 2>&1; then \
		echo "Image $(N8N_IMAGE) missing — running make n8n-build first..."; \
		$(MAKE) n8n-build; \
	fi
	N8N_IMAGE="$(N8N_IMAGE)" HTTP_PROXY="$(HTTP_PROXY)" HTTPS_PROXY="$(HTTPS_PROXY)" \
		docker compose --profile n8n up -d --pull missing
	@echo ""
	@echo "n8n visual editor: http://localhost:5678"
	@echo "Then: make n8n-import"

$(VENV)/bin/python:
	$(MAKE) install

down:
	docker compose --profile n8n down

status:
	docker compose --profile n8n ps -a

logs:
	docker compose --profile n8n logs -f --tail=100

migrate:
	$(ALEMBIC) upgrade head

seed:
	$(PYTHON) scripts/seed_synthetic_data.py

ingest-youtube:
	@echo "Requires YOUTUBE_API_KEY in .env — see docs/guides/youtube-demo-ingest.md"
	$(PYTHON) scripts/ingest_youtube.py

classify:
	@echo "Requires ANTHROPIC_API_KEY in .env — falls back to keyword labels without it"
	$(PYTHON) scripts/classify_content.py

public-report:
	$(PYTHON) scripts/public_signal_report.py

dashboard:
	$(STREAMLIT) run dashboard/Home.py --server.headless true

api:
	$(UVICORN) app.api.main:app --reload --host 0.0.0.0 --port 8000

report:
	$(PYTHON) scripts/generate_weekly_report.py --days 7

n8n-import:
	docker compose --profile n8n exec -u node -w /opt/n8n n8n \
		/opt/n8n/node_modules/.bin/n8n import:workflow --input=/import/weekly_growth_report.json
	@echo "Imported. Open http://localhost:5678 and refresh Workflows."

test:
	$(PYTEST) -q

eval:
	$(PYTEST) -q evaluation/tests

lint:
	$(RUFF) check app tests scripts dashboard evaluation
