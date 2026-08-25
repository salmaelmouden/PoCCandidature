# Growth Intelligence AI

AI-native growth analytics, decision support, and automation for content-driven acquisition.

**▶ Live — <https://poccandidature-production.up.railway.app>**  
The landing page is the three-minute read. Everything else in this repository is the
evidence behind it.

> Independent portfolio project, **not affiliated with Finary**. **Hybrid data:** labelled
> synthetic funnel metrics + real **public** YouTube catalogue metadata via the official
> Data API (read-only). No private APIs, no internal analytics, no logos, no proprietary
> datasets. Public view/like/comment counts only — signups and conversion are not observable
> from outside a channel and are never inferred.

## What it found

Four readings of a public YouTube catalogue of ~950 videos, each ending in the editorial
move it implies. The figures are deliberately not repeated here: they are derived live from
the catalogue on every render, and a number copied into a README is a number that goes
quietly wrong.

1. **The format decides the hook, not the other way round.** Authority wins at length,
   the contrarian angle wins in Shorts, and the most-used hook in the whole catalogue —
   the question — wins in neither. Changing it costs nothing: same subject, same shoot,
   same edit, different title for the destination format.
2. **Narrative needs length.** The same topic ranks near the top in long form and near the
   bottom as a Short. Narrative is the register that demands the least prior financial
   literacy, so serving it short strips it of what makes it work.
3. **The largest editorial bet is the least-travelled topic.** A quarter of the long-form
   catalogue sits on the subject that circulates least. This one recommends **nothing**:
   if that volume buys audience qualification rather than reach, the choice is sound, and
   the metric that settles it is not visible from outside.
4. **The catalogue and the premium tier do not look at each other.** Subjects that
   presuppose existing capital hold a small share of production next to entry-level ones.
   A claim about **production mix**, never about audience — who watches what is not
   observable externally, and the topic classification it rests on is named on the page
   rather than buried in it.

Three of the four name a metric only internal data can supply. None infers signups or
conversion from public signals, because neither is observable from outside a channel.

### And one reading that is not about the editorial line

The four above ask what makes a video circulate. A fifth asks what happens next: does a
video that worked offer a way in at all? The description is the only part of the
acquisition path a channel publishes, so three questions can be answered from outside —
whether a link to the product exists, whether it sits above the fold, and whether it
carries anything an analytics tool could attribute a signup to. A **placement** claim in
all three cases. It can say *"no door here"*; it can never say *"nobody came in"*.

It is also the one reading that needs no classifier, so it covers the whole ingested
catalogue rather than the labelled subset the reach index is restricted to.

## The bug that shaped the design

An `int()` truncation in the synthetic generator floored the funnel's terminal stage to
near zero. The chain read that as a 100 % dropoff, the strategist agent turned it into a
confident `[P0] Fix Premium leak` with a full action plan, and the automation shipped it
every Monday. The evaluation suite was green throughout — it had never tested the agents
on a degenerate input.

The fix was not a better prompt. A deterministic skill (`metric_validation`) now qualifies
metrics before an agent sees them, and a deterministic post-condition downgrades any P0/P1
aimed at a stage a warning covers. The correction never depends on the model complying, and
it is testable without one. Written up in
[`docs/plans/phase-16-trustworthy-automation.md`](docs/plans/phase-16-trustworthy-automation.md),
decided in [`ADR-009`](docs/decisions/ADR-009-data-quality-gate.md).

## Reading this repo in three minutes

| If you want | Go to |
|---|---|
| The findings | Live app → **En bref** |
| The full argument, with charts and coverage | Live app → **Catalogue public** |
| Where the funnel's entry point sits, if it exists | Live app → **La porte d'entrée**, or `make cta-report` — placement only, never conversion |
| Proof it is not a one-off script | `scripts/refresh_catalogue.py`, `ingest_runs`, and the freshness row on the catalogue page — *last checked* and *last changed* are separate on purpose |
| Where an LLM is allowed to write | [`ADR-008`](docs/decisions/ADR-008-llm-text-labelling.md) — titles only, versioned in the database; no arithmetic |
| How agents are stopped from over-claiming | [`ADR-009`](docs/decisions/ADR-009-data-quality-gate.md), `app/skills/metric_validation/` |
| The working method | [`AGENTS.md`](AGENTS.md), `.cursor/rules/`, `.cursor/skills/` — plan → critic → test-writer → implement |
| Whether it is tested | `make test` (405), `make eval` (pinned agent fixtures) |

## Current status

**Phase 18** — the funnel's public entry point: where the product link sits in the
descriptions, whether it is visible, and whether anything could attribute a signup
to it. Placement only, and the one reading here that needs no classifier.

```bash
make install      # once (venv is mounted into app containers)
make up           # core stack (n8n optional — corporate Docker Hub often blocked)
make status
make eval         # agent evaluation suite
make public-report
make cta-report   # where the funnel's entry point sits in the descriptions
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
- [x] **En bref** landing page (`dashboard/views/brief.py`) — four readings of the
      real catalogue with the move each implies, derived through `dashboard/brief.py`
      from the same live report the full page reads, so the summary cannot drift from
      the analysis it summarises
- [x] Production mix read against the business model: what share of the catalogue
      treats subjects that presuppose capital. A **mix** claim, never an audience
      one — who watches is not observable from outside a channel — and the topic
      classification it rests on is named in the rendered text, not buried in it
- [x] Navigation reordered and renamed: the real catalogue leads, the synthetic funnel
      sits under a group that says so before a reader clicks it
- [x] W3 — `memo_generation`: the weekly French editorial memo over the real
      catalogue. Composes, never computes — every figure arrives from
      `public_signal_analysis` / `catalogue_movement`, so the memo cannot disagree
      with the page describing the same week. Two **deterministic post-conditions**
      run before it is written or returned, because a bad memo looks exactly like a
      good one once it is in an inbox:
      `undeclared_figures` names any number the composer never emitted (a hand-typed
      "environ 40 %" is rejected), and `funnel_vocabulary_leaks` confines signup and
      conversion vocabulary to the one section that exists to say those things are
      invisible from outside a channel. No recommendation section, on purpose:
      recommendations are reasoning (ADR-002), and a scheduled delivery must not
      depend on a model call. Absence degrades into a sentence, never a zero — no
      second snapshot, one-day resolution, no refresh run, and thin dimension rows
      each say so. `make memo` / `memo-write` / `memo-loop`,
      `POST /api/memo/editorial`, dated markdown under `reports/`
- [x] W4 — the automation made observable. `automation_runs` (migration `005`) +
      `AutomationRunRepository`; every execution is recorded **including the ones
      that produce nothing**, because writing nothing on failure makes a broken
      job indistinguishable from one that was not due. The CLI and the endpoint
      both record before they return, in their own transaction, so the record
      survives whatever went wrong in the one building the memo.
      `app/services/automation.py` separates *last run* from *last success* — the
      Phase 14 distinction one level up — and names three states rather than one:
      `failing` (it errored), `stale` (it succeeded, then silently stopped being
      invoked — the failure mode with no error message), `never`. Second n8n
      canvas on a Monday 07:00 schedule with a failure branch, since the endpoint
      answers 500 rather than shipping a memo that failed a post-condition. In
      production the schedule is a Railway cron service (`railway.memo.json`,
      `0 7 * * 1`) — n8n runs on a laptop, so without it "weekly" would be true
      locally and false on the deployed app. That container's filesystem is
      discarded on exit, so the memo's markdown is stored **on the run** and read
      back from there; an `artifact_path` pointing at a file that no longer exists
      is worse than no path. Dashboard page **Automatisation → Runs planifiés**
      shows the history and the last memo; the verdict is computed in the service,
      the page renders it

### Phase 17

The analysis said an opening register underperforms. That is not what gets acted
on in an editorial meeting — titles are. This phase closes the last gap between a
finding and a decision, under constraints that keep it honest.

- [x] **Dix titres** page (`dashboard/views/titres.py`) — ten rewrite proposals for
      real long-form videos, each beside the original and its live reach index
- [x] `build_title_evidence` — the candidate list is a **query**, never a curated
      list: long form ≥ 8 min, `question` hook, reach index below its own cohort
      median, worst first. A video that climbs out of the bottom leaves the page,
      and its rewrite goes with it
- [x] Two hook rankings carried side by side because they **disagree** — `autorite`
      leads all long-form video and is not even reportable inside the recurring
      patrimoine series, where `chiffre` wins. A rule drawn from the global ranking
      alone would be applied backwards exactly where it is applied most
- [x] `gap_sentence` picks the best register clearing `THIN_THRESHOLD`, not the top
      row — the real series ranking is led by an 8-video median that must not drive
      a publishing calendar
- [x] Two natural experiments surfaced from the catalogue itself — same guest and
      same subject, or same subject four months apart — cited with **live** indices
      and dropped rather than restated if the cited video leaves the indexed set
- [x] Writing constraints, stated on the page: no invented figures (euro amounts
      appear as `[slots]` for whoever watched the video) and no asserted verdicts
      about a real person's finances
- [x] `tests/dashboard/test_rewrites.py` — id-keyed pairing, thin-leader skipping,
      precedent resolution, and graceful degradation to fewer cards, never blank ones

### Phase 18

The four editorial readings ask what makes a video circulate. This one asks what
happens after it does — and it is the only reading here that touches the top of
the conversion funnel without inferring a single thing about conversion.

- [x] `cta_analysis` skill — where the product link sits in a public description:
      present or absent, above the fold or behind "plus", carrying a campaign
      parameter or not. **Placement, never conversion**: it can say "no door
      here", never "nobody came in"
- [x] The product domain is **derived**, not configured — the most-linked domain
      outside YouTube and the social platforms, returned with the sentence that
      justifies it. The rejected candidates stay in the table on the page, because
      an assumption nobody can check is a hidden assumption
- [x] Only links YouTube actually makes clickable are counted (`http(s)` or a
      `www.` prefix). A bare `domain.com` mid-sentence is text, and counting it
      would inflate the number of doors
- [x] Three attribution states, not two: a `go.` redirect or a shortener is
      **opaque**, not untracked — it may append a campaign after the hop, and the
      URL text cannot settle it. Folding the two together would manufacture a
      finding
- [x] Above the fold is counted in **rendered lines**, and the raw character
      offset ships beside it — the threshold is an approximation of where YouTube
      cuts, so the page also carries the median offset, which needs no threshold
- [x] No classifier required, so this reading covers the whole ingested catalogue
      rather than the labelled subset the reach index is restricted to
- [x] **La porte d'entrée** page + `make cta-report`, and the ten most-watched
      videos with no entry point — a query, not a list: it re-runs at every ingest
- [x] `finalize()` in `dashboard/charts.py` ended on `.configure(background=...)`,
      which **replaces** the config object rather than merging into it. Every
      chart in the app had been silently dropping its axis, legend and view
      styling on the last line of the builder. Background is now a top-level
      chart property
