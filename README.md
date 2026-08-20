# Growth Intelligence AI

AI-native growth analytics, decision support, and automation for content-driven acquisition.

> Independent portfolio project. All demo metrics use **labelled synthetic data**. Not affiliated with Finary; no private APIs, logos, or proprietary datasets.

## Current status

**Phase 3 — YouTube ingestion** on branch `phase-3-youtube-ingestion`.

Phase 1 Postgres: `make up && make migrate && make seed` (host port **5434**).  
Optional live ingest: set `YOUTUBE_API_KEY` + `YOUTUBE_CHANNEL_ID`, then `make ingest-youtube`.

## Quick start (Phase 1)

```bash
cp .env.example .env
make install
make up
make migrate
make seed
make test
```

Synthetic seed is idempotent and clearly labelled (`synthetic_v1`).

## YouTube ingest (Phase 3)

```bash
# in .env — never commit secrets
YOUTUBE_API_KEY=...
YOUTUBE_CHANNEL_ID=...
make ingest-youtube
```

Public Data API stats are **lifetime cumulative** snapshots labelled `youtube_api` (`is_synthetic=false`).

## Architecture (target)

```text
YouTube API → youtube_ingestion → PostgreSQL
                                      ↓
                              Analytics skills
                                      ↓
                         growth_orchestrator_agent
                    ┌─────────────┼─────────────┐
                    ↓             ↓             ↓
            data_analyst   strategist   experiment_analyst
                    └─────────────┼─────────────┘
                                  ↓
                     Recommendations → n8n / reports

UI: Streamlit · API: FastAPI · Observability: Langfuse
```

Layers: Presentation → API/Dashboard → Application → Agents → Skills → Repositories → DB/External APIs.

**Agents reason. Skills execute. Database is the source of truth.**

## Repository layout

```text
.cursor/rules/          # Cursor project rules
.cursor/skills/         # AI-assisted development skills
app/db/                 # Models, repositories, synthetic loader
alembic/                # Migrations
dashboard/              # Streamlit (Phase 4+)
evaluation/             # Agent evaluation structure
n8n/workflows/          # Automation (Phase 9+)
docs/                   # Architecture, conventions, ADRs
tests/                  # Tests
scripts/                # Seed / ops scripts
```

## Engineering system

- Constitution & rules: `.cursor/rules/`
- Dev skills: `.cursor/skills/`
- Data model: `docs/architecture/data-model.md`
- Naming: `docs/conventions/naming.md`
- Architecture: `docs/architecture/overview.md`
- ADRs: `docs/decisions/`

## Product questions

1. Which content generates traffic / signups / premium users?
2. Which topics have high reach but poor conversion?
3. Which channels perform best? Where does the funnel leak?
4. What changed vs last period — and why?
5. What should we do? What experiment should we run?
6. Can analysis be automated?

## Tech stack

Python 3.12+ · PostgreSQL · SQLAlchemy · Alembic · Pydantic · pytest · Docker Compose  
(FastAPI, Streamlit, n8n, Langfuse in later phases)

## Development workflow

Plan → critic → test-writer → implement. See `AGENTS.md`.

## Definition of done (so far)

### Phase 0

- [x] Cursor rules & development skills
- [x] Conventions, contracts, ADRs, evaluation structure

### Phase 1

- [x] Docker Compose Postgres
- [x] SQLAlchemy models + Alembic migration
- [x] Repository layer
- [x] Labelled synthetic generator + idempotent seed
- [x] Unit tests for generator + repositories

### Phase 2

- [x] `funnel_analysis` skill (rates, dropoffs, bottleneck, period compare)
- [x] `content_analysis` skill (documented Content Value Score, gaps)
- [x] `anomaly_detection` skill (z-score, IQR, % change, rolling mean)
- [x] Skill unit tests

### Phase 3

- [x] `youtube_ingestion` skill (Data API client, transform, idempotent load)
- [x] CLI `make ingest-youtube`
- [x] Mocked HTTP unit tests (no live key required)
