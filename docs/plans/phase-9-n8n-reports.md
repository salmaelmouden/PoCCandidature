# Plan: Phase 9 — n8n + report generation

**Status:** Implemented  
**Branch:** `phase-9-n8n-reports`  
**Scope:** `report_generation` skill, FastAPI report endpoint, **n8n with visual editor** in Docker Compose, importable weekly workflow.  
**Out of scope:** Phase 10 evaluation polish, production auth hardening, live email delivery.

## Goals

1. Deterministic weekly growth report from analytics (+ optional orchestrator summary).
2. HTTP API n8n can call (`POST /api/reports/weekly`).
3. **Visual n8n:** service on http://localhost:5678 with canvas workflow (sticky notes + nodes).

## Flow

```text
n8n UI (Schedule | Manual)
        → HTTP Request → gia-api:/api/reports/weekly
        → show markdown / save payload
```

## DoD

- [x] report_generation skill + tests
- [x] FastAPI + docker `api` service
- [x] n8n service + workflow JSON + import docs
- [x] Makefile / README updated
- [ ] Commit/push
