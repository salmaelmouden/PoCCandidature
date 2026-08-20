# Growth Intelligence AI
.PHONY: help install up down status logs migrate seed ingest-youtube dashboard test lint

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
ALEMBIC := $(VENV)/bin/alembic
STREAMLIT := $(VENV)/bin/streamlit
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

help:
	@echo "Docker stack (recommended):"
	@echo "  make install    - once: create .venv + deps (needed by containers)"
	@echo "  make up         - start postgres, migrate, seed, dashboard"
	@echo "  make status     - docker compose ps -a (running vs exited)"
	@echo "  make logs       - follow container logs"
	@echo "  make down       - stop stack"
	@echo ""
	@echo "Local venv targets: migrate / seed / dashboard / test / lint / ingest-youtube"

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
	@echo "Stack starting. Check status with: make status"
	@echo "Dashboard: http://localhost:8501"

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
	$(PYTHON) scripts/ingest_youtube.py

dashboard:
	$(STREAMLIT) run dashboard/Home.py --server.headless true

test:
	$(PYTEST) -q

lint:
	$(RUFF) check app tests scripts dashboard
