# Growth Intelligence AI
.PHONY: help install up down migrate seed ingest-youtube dashboard test lint

help:
	@echo "Targets:"
	@echo "  make install         - install package + dev deps"
	@echo "  make up              - start Postgres (Docker Compose)"
	@echo "  make down            - stop Postgres"
	@echo "  make migrate         - run Alembic migrations"
	@echo "  make seed            - load labelled synthetic data (idempotent)"
	@echo "  make ingest-youtube  - ingest YouTube channel via Data API"
	@echo "  make dashboard       - run Streamlit dashboard"
	@echo "  make test            - run pytest"
	@echo "  make lint            - run ruff"

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

ingest-youtube:
	python scripts/ingest_youtube.py

dashboard:
	streamlit run dashboard/Home.py

test:
	pytest -q

lint:
	ruff check app tests scripts dashboard
