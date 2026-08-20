# Architecture Overview

**Status:** Phase 3 — YouTube ingestion

## Product loop

```text
OBSERVE → MEASURE → UNDERSTAND → DECIDE → TEST → AUTOMATE → MEASURE AGAIN
```

## Runtime layers

```text
Presentation (Streamlit)
        ↓
API / Dashboard adapters (FastAPI + thin UI)
        ↓
Application services
        ↓
Agents (reasoning, orchestration)
        ↓
Skills (deterministic capabilities)
        ↓
Repositories
        ↓
PostgreSQL / External APIs (e.g. YouTube)
```

## Component map (target)

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
                          Recommendations
                                  ↓
                     report_generation / n8n
```

**Observability:** Langfuse on the AI execution layer.  
**UI:** Streamlit. **API:** FastAPI.

## Dependency rules

See `.cursor/rules/02-architecture.mdc`.

## Planned tables (Phase 1)

Implemented: `videos`, `video_daily_metrics`, `acquisition`, `users`, `experiments`, `experiment_results`, `analytics_snapshots`.

See [data-model.md](data-model.md).

## Synthetic data policy

All demo data is **synthetic** and labelled as such. Not Finary data. No private APIs or proprietary datasets.
