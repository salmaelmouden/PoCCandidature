# Plan: Phase 1 — Data Foundation

**Status:** Implemented (awaiting Phase 1 approval)  
**Scope:** PostgreSQL, SQLAlchemy models, repositories, labelled synthetic data, Alembic, Docker Compose.  
**Out of scope:** Analytics skills, agents, Streamlit, YouTube API, Langfuse, n8n.

## Goals

1. Runnable Postgres via Docker Compose.
2. Typed SQLAlchemy 2.0 models for all planned tables.
3. Repository layer (no raw SQL from future agents).
4. Idempotent synthetic seed with seasonality, anomalies, and a known Premium conversion decline (YouTube-heavy) for later demos.
5. Alembic migrations.
6. Unit tests for generator determinism and repository upserts (SQLite or Postgres).
7. Update docs/README/Makefile/AGENTS for Phase 1 commands.

## Tables

| Table | Purpose |
|-------|---------|
| `videos` | Content catalog + topic |
| `video_daily_metrics` | Daily views/likes/comments per video |
| `acquisition` | Daily funnel facts by channel/topic/video |
| `users` | Synthetic user journey (signup → activate → premium) |
| `experiments` | Experiment metadata |
| `experiment_results` | Per-variant results |
| `analytics_snapshots` | Point-in-time metric snapshots |

All rows carry `is_synthetic=true` (or dataset label) where applicable.

## Architecture notes

- Config via env / pydantic-settings.
- Repositories encapsulate persistence.
- Seed script: extract (generate) → transform (normalize) → load (upsert).
- Dependencies: sqlalchemy, psycopg, pydantic-settings, alembic, pytest.

## Demo narrative baked into seed

- Recent period: Premium conversion drop concentrated in YouTube channel.
- Mix of high-reach/low-conversion vs high-conversion/low-reach topics.
- One traffic anomaly spike; weekend seasonality.

## Definition of done

- [x] `docker compose up -d` starts Postgres (compose file ready)
- [x] Migrations apply (Alembic `001_initial_schema`)
- [x] `make seed` loads synthetic data idempotently
- [x] Tests cover generator + repository behavior (8 passed)
- [x] Docs/phases updated; no secrets committed
