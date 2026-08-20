# Growth Intelligence AI

AI-native growth analytics, decision support, and automation for content-driven acquisition.

> Independent portfolio project. All demo metrics use **labelled synthetic data**. Not affiliated with Finary; no private APIs, logos, or proprietary datasets.

## Current status

**Phase 0 — Engineering foundation** (no application runtime yet).

Approved next step after Phase 0: **Phase 1 — Data foundation**.

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
app/                    # Runtime application (Phase 1+)
dashboard/              # Streamlit (Phase 4+)
evaluation/             # Agent evaluation structure
n8n/workflows/          # Automation (Phase 9+)
docs/                   # Architecture, conventions, ADRs
tests/                  # Cross-cutting tests
scripts/                # Ops / seed scripts (Phase 1+)
```

## Engineering system

- Constitution & rules: `.cursor/rules/`
- Dev skills: `.cursor/skills/`
- Naming: `docs/conventions/naming.md`
- Architecture: `docs/architecture/overview.md`
- Agent taxonomy: `docs/agents/taxonomy.md`
- Skill taxonomy: `docs/skills/taxonomy.md`
- ADRs: `docs/decisions/`
- Contracts: `docs/templates/`

## Product questions

1. Which content generates traffic / signups / premium users?
2. Which topics have high reach but poor conversion?
3. Which channels perform best? Where does the funnel leak?
4. What changed vs last period — and why?
5. What should we do? What experiment should we run?
6. Can analysis be automated?

## Tech stack (planned)

Python 3.12+ · FastAPI · PostgreSQL · SQLAlchemy · Pydantic · Pandas/NumPy/SciPy · pytest · Streamlit · n8n · Langfuse · Docker Compose

## Development workflow

Plan → critic → test-writer → implement. See `AGENTS.md` and `docs/architecture/development.md`.

## Phase 0 definition of done

- [x] Cursor rules
- [x] Development skills
- [x] Naming / architecture / agent / skill conventions
- [x] Contract templates
- [x] ADR structure + initial ADRs
- [x] Evaluation structure
- [x] Documentation skeleton
- [x] README architecture section

Application checkboxes (Postgres, agents, dashboard, …) start in later phases.
