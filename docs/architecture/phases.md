# Phases

Do not implement later phases until the current phase is approved.

| Phase | Name | Status |
|-------|------|--------|
| 0 | Engineering foundation | Done |
| 1 | Data foundation (Postgres, models, synthetic data) | Done (Docker seeded) |
| 2 | Analytics skills (funnel, content, anomaly) | Done |
| 3 | YouTube ingestion | **Done (awaiting push/merge)** |
| 4 | Dashboard (overview, acquisition, content, funnel) | Not started |
| 5 | Data Analyst agent | Not started |
| 6 | Strategist + Orchestrator | Not started |
| 7 | Experimentation skill + agent | Not started |
| 8 | Langfuse observability | Not started |
| 9 | n8n + report generation | Not started |
| 10 | Evaluation + polish | Not started |

## Branching convention

Each phase is developed on `phase-N-<slug>`, committed, and pushed. Merge to `main` when approved.

## MVP priority

- **P0:** foundation, Postgres, synthetic data, funnel/content analysis, dashboard, analyst, strategist, orchestrator
- **P1:** YouTube, experiment agent, n8n
- **P2:** Langfuse, evaluation framework, advanced anomalies, polish
