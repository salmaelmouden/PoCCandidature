# Phases

Do not implement later phases until the current phase is approved.

| Phase | Name | Status |
|-------|------|--------|
| 0 | Engineering foundation | Done |
| 1 | Data foundation (Postgres, models, synthetic data) | Done |
| 2 | Analytics skills (funnel, content, anomaly) | Done |
| 3 | YouTube ingestion | Done |
| 4 | Dashboard (overview, acquisition, content, funnel) | Done |
| 5 | Data Analyst agent | Done |
| 6 | Strategist + Orchestrator | Done |
| 7 | Experimentation skill + agent | Done |
| 8 | Langfuse observability | Done |
| 9 | n8n + report generation | Done |
| 10 | Evaluation + polish | Done |
| 11 | LLM content classification | Done |
| 12 | Public-signal analysis | Done |
| 13 | Catalogue insights + demo surface | Done |
| 14 | Catalogue refresh + Railway deploy | Done |
| 15 | Dashboard design system (French UI, themed charts) | Done |

## Branching convention

Each phase is developed on `phase-N-<slug>`, committed, and pushed. Merge to `main` when approved.

## MVP priority

- **P0:** foundation, Postgres, synthetic data, funnel/content analysis, dashboard, analyst, strategist, orchestrator
- **P1:** YouTube, experiment agent, n8n, classification, public signals, insights, refresh, deploy, design system
- **P2:** Langfuse, evaluation framework, polish
