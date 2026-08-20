# Growth Intelligence AI
.PHONY: help install up down migrate seed test lint

help:
	@echo "Targets:"
	@echo "  make install  - install package + dev deps"
	@echo "  make up       - start Postgres (Docker Compose)"
	@echo "  make down     - stop Postgres"
	@echo "  make migrate  - run Alembic migrations"
	@echo "  make seed     - load labelled synthetic data (idempotent)"
	@echo "  make test     - run pytest"
	@echo "  make lint     - run ruff"

install:
	python -m pip install -e ".[dev]"

up:
	docker compose up -d

down:
	docker compose down

migrate:
	alembic upgrade head

seed:
	python scripts/seed_synthetic_data.py

test:
	pytest -q

lint:
	ruff check app tests scripts
