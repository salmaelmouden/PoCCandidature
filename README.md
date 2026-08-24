# Growth Intelligence AI

AI-native growth analytics, decision support, and automation for content-driven acquisition.

> Independent portfolio project, **not affiliated with Finary**. **Hybrid data:** labelled
> synthetic funnel metrics + real **public** YouTube catalogue metadata via the official
> Data API (read-only). No private APIs, no internal analytics, no logos, no proprietary
> datasets. Public view/like/comment counts only — signups and conversion are not observable
> from outside a channel and are never inferred.

## Current status

**Phase 16** — trustworthy automation (W1 + W2 shipped, W3 + W4 pending) and the
**En bref** landing page: the three-minute reading of the real catalogue, every
number derived from the same live report as the full analysis.

```bash
make install      # once (venv is mounted into app containers)
make up           # core stack (n8n optional — corporate Docker Hub often blocked)
make status
make eval         # agent evaluation suite
make public-report
make refresh-loop # keep the catalogue current (every 15 min)
# Dashboard: http://localhost:8501  (Catalogue public = real YouTube track)
# API docs:  http://localhost:8000/docs
# n8n UI:    make n8n-build && make up-n8n
# Demo:      docs/guides/demo-script.md
# Narrative: docs/insights/catalogue-finary.html
# Deploy:    docs/guides/deploy-railway.md
```

| Container | Role | Expected state |
|-----------|------|----------------|
| `gia-postgres` | PostgreSQL | **running** (healthy) |
| `gia-migrate` | Alembic | **exited (0)** after migrate |
| `gia-seed` | Synthetic seed | **exited (0)** after seed |
| `gia-api` | FastAPI reports | **running** → http://localhost:8000 |
| `gia-dashboard` | Streamlit | **running** → http://localhost:8501 |
| `gia-n8n` | n8n visual editor | **optional** (`make up-n8n`) → http://localhost:5678 |

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

After a change to the generator, `make seed` is not enough: it upserts, so it
corrects the rows it regenerates and leaves behind any it no longer produces (the
window slides with `as_of`, and the `syn_user_*` keys track signup volume). Use
`make seed-reset` to replace the labelled dataset — the ingested catalogue
(`youtube_api`) is left alone. For the deployed database, see
[deploy-railway.md](docs/guides/deploy-railway.md#re-seeding-after-a-change-to-the-generator).

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
dashboard/              # Streamlit — router + views/ + pure presentation layer
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

### Phase 8

- [x] Optional Langfuse tracing (`app/observability`) — no-op without keys
- [x] Orchestrator / agents / analyst tools instrumented
- [x] Sanitize secrets; Streamlit `flush_tracing`
- [x] Guide: `docs/guides/langfuse.md`

### Phase 9

- [x] `report_generation` skill + weekly report service
- [x] FastAPI `POST /api/reports/weekly` (`gia-api`)
- [x] n8n visual UI in Docker (`gia-n8n` :5678) + importable canvas workflow
- [x] Guide: `docs/guides/n8n-weekly-report.md`

### Phase 10

- [x] Runnable eval suite (`make eval`) + scoring helpers
- [x] Pinned synthetic fixtures for CI
- [x] Interview demo script (`docs/guides/demo-script.md`)
- [x] Docs / phases polish (MVP complete)

### Phase 11

- [x] Real Finary public catalogue ingested (952 videos, 2021→2026)
- [x] `content_classification` skill — `topic` + `hook_type` via `claude-opus-5`,
      deterministic keyword fallback when no key is set
- [x] Versioned `video_classifications` table (migration `002`)
- [x] `make classify` + `scripts/classify_content.py`
- [x] ADR-008 — where an LLM may write to the database (amends ADR-002)
- [x] Fixes: API key no longer logged, blank `.env` placeholders no longer override
      defaults, corporate TLS interception configurable (`CA_BUNDLE_PATH`)

### Phase 12

- [x] `public_signal_analysis` skill — cohort-normalised reach index + engagement rate,
      reported per format (the catalogue is 52 % Shorts)
- [x] `services/public_signals.py` loader (excludes fallback-labelled rows)
- [x] `make public-report` — evidence table, facts only
- [x] Coverage reported explicitly: 926/952 videos indexed, 26 excluded as thin cohorts

### Phase 13

- [x] Streamlit **Catalogue public** page — five readings whose every number is
      derived from the live report, so the narrative cannot drift after an ingest
- [x] `dashboard/catalogue_view.py` — pure chart/table helpers, unit-tested
- [x] Narrative HTML `docs/insights/catalogue-finary.html`
- [x] Demo script covers synthetic funnel **and** public catalogue tracks
- [x] Docs / phases synced

### Phase 14

- [x] `scripts/refresh_catalogue.py` — ingest + classify, once or on a loop, with
      exponential backoff and a graceful SIGTERM stop (`make refresh` / `make refresh-loop`)
- [x] `ingest_runs` table (migration `003`) — freshness is a property of the run,
      not of the data: a same-day re-ingest updates rows, and unchanged counters
      write nothing at all
- [x] Page separates **last checked** from **last changed**, with minute resolution
- [x] `Dockerfile` + `railway.json` + `docs/guides/deploy-railway.md`
- [x] `DATABASE_URL` from managed providers rewritten to the psycopg 3 driver
- [x] `YouTubeClient` honours `CA_BUNDLE_PATH` (previously only the Anthropic client did)

### Phase 15

- [x] Design system — `dashboard/theme.py` (light/dark tokens + stylesheet) mirrored
      by `.streamlit/config.toml`, so Streamlit's own theme switch drives both the
      widgets it paints and the parts we draw
- [x] Brand chrome and data palette kept apart: the brand green never encodes a
      value, and no series colour is reused as chrome
- [x] Palettes **validated** rather than eyeballed — categorical (CVD ΔE 9.1 light /
      8.4 dark) and a brand-green ordinal ramp for the funnel, each checked against
      the surface it actually renders on; the sub-3:1 light slots ship a table twin
- [x] `st.navigation` router (`dashboard/Home.py`) with grouped, French, icon-bearing
      pages under `dashboard/views/` — replaces the filename-driven `pages/` nav
- [x] Raw `st.dataframe` dumps replaced by charts with a form chosen per job: funnel
      = ordinal ramp, period change = diverging bars, channel rates = one shared
      axis, content = emphasis scatter
- [x] Ergonomics — filters survive page switches, agent results survive a rerun,
      example questions as pills, `st.status` while an agent works
- [x] Motion is short, staggered, and disabled under `prefers-reduced-motion`
- [x] `OverviewSnapshot.daily_series` — per-stage sparklines without a page reaching
      into a repository
- [x] `tests/dashboard/` covers tokens, French formatting, HTML escaping and every
      chart spec in both themes

### Phase 16

- [x] W1 — stochastic rounding in the synthetic generator; the `int()` truncation at
      day × channel × topic grain had floored the Premium stage to 0,22 % against a
      configured ~12 %, and the chain was shipping a confident `[P0] Fix Premium leak`
      built on it. Per-transition invariants derived from the module constants
- [x] W2 — `metric_validation` skill + a deterministic post-condition that downgrades
      any P0/P1 aimed at a stage a warning covers, so the fix never depends on the
      model obeying a prompt (ADR-009). Eval case + fixture for the degenerate funnel
- [x] **En bref** landing page (`dashboard/views/brief.py`) — three readings of the
      real catalogue with the move each implies, derived through `dashboard/brief.py`
      from the same live report the full page reads, so the summary cannot drift from
      the analysis it summarises
- [x] Navigation reordered and renamed: the real catalogue leads, the synthetic funnel
      sits under a group that says so before a reader clicks it
- [ ] W3 — `memo_generation`: weekly French editorial memo over the real catalogue
- [ ] W4 — `automation_runs` (migration `004`), scheduled n8n memo, run history
