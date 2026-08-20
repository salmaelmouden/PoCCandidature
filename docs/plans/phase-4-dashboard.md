# Plan: Phase 4 — Dashboard

**Status:** Implemented  
**Branch:** `phase-4-dashboard`  
**Scope:** Streamlit pages Overview, Acquisition, Content, Funnel + application service glue.  
**Out of scope:** AI chat agent, experiments UI, FastAPI, n8n, Langfuse.

## Design

```text
Streamlit pages → app.services.dashboard → skills + repositories → Postgres
```

Pages are presentation-only. Synthetic data is labelled in-banner.

## DoD

- [x] Service + pages
- [x] Tests for service (SQLite)
- [x] Docs + Makefile
- [ ] Commit/push branch
