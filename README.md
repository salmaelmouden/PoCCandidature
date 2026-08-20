# Growth Intelligence AI

AI-native growth analytics, decision support, and automation for content-driven acquisition.

> Independent portfolio project. **Hybrid data:** labelled synthetic funnel metrics + optional real public YouTube Data API ingest. Not affiliated with Finary; no private APIs, logos, or proprietary datasets.

## Current status

**Phase 7 — Experimentation** on branch `phase-7-experimentation`.

```bash
make install   # once (venv is mounted into app containers)
make up
make status
# open http://localhost:8501 → Orchestrator or Experiments
```

| Container | Role | Expected state |
|-----------|------|----------------|
| `gia-postgres` | PostgreSQL | **running** (healthy) |
| `gia-migrate` | Alembic | **exited (0)** after migrate |
| `gia-seed` | Synthetic seed | **exited (0)** after seed |
| `gia-dashboard` | Streamlit | **running** → http://localhost:8501 |

App containers mount the project + `.venv` (no pip install inside Docker — avoids TLS/PyPI issues).

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

## Real YouTube ingest (Phase 3, optional but recommended for demos)

You do **not** need your own channel. Default public demo channel: **Two Cents (PBS)**  
`UCL8w_A8p8P1HWI3k6PR5Z6w` — https://www.youtube.com/@TwoCentsPBS

1. Create a free [YouTube Data API v3 key](https://console.cloud.google.com/) (details: [`docs/guides/youtube-demo-ingest.md`](docs/guides/youtube-demo-ingest.md)).
2. Put only the key in `.env` (never commit it):

```bash
YOUTUBE_API_KEY=your_key_here
# channel already defaults in .env.example
make ingest-youtube
```

| Layer | Source | Label |
|-------|--------|--------|
| Funnel / Premium story | Synthetic seed | `synthetic_v1` |
| Video metadata + public stats | YouTube Data API | `youtube_api` |

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

### Phase 4

- [x] Streamlit Overview / Acquisition / Content / Funnel
- [x] Application service glue (no business logic in UI)
- [x] Service unit tests

### Phase 5

- [x] `growth_data_analyst_agent` (tools + FACT/INTERPRETATION report)
- [x] Deterministic synthesizer (no LLM required for CI/demos)
- [x] Streamlit Analyst page
- [x] Agent unit tests

### Phase 6

- [x] `growth_strategist_agent` (RECOMMENDATION playbook grounded in analyst)
- [x] `growth_orchestrator_agent` (routing + synthesis, ADR-004)
- [x] Streamlit Orchestrator page
- [x] Routing / strategist unit tests

### Phase 7

- [x] `experiment_analysis` skill (lift, CI, two-proportion z-test)
- [x] `growth_experiment_analyst_agent` (analyze + propose)
- [x] Orchestrator experiment route + Experiments page
- [x] Skill / agent unit tests
