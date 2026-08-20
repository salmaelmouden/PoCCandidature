# Interview / portfolio demo script

~10–12 minutes. Stack: `make up` (optional `make up-n8n` after `make n8n-build`).

## Narrative

> Hybrid growth intelligence: labelled synthetic funnel + optional public YouTube ingest.  
> Agents reason; skills compute; Postgres is source of truth. No private Finary data.

## Walkthrough

1. **Overview** — http://localhost:8501  
   KPIs, bottleneck, anomalies. Point at `synthetic_v1` provenance banner.

2. **Analyst** — “Why did Premium conversion decrease?”  
   Show FACT vs INTERPRETATION, tool calls, primary driver (often YouTube).

3. **Orchestrator** — same question vs “What should we do about Premium?”  
   Route changes: analyst-only → analyst + strategist recommendations.

4. **Experiments** — “Did the YouTube CTA experiment work?”  
   Decision hint `ship_treatment` from deterministic stats skill.

5. **Automation** — http://localhost:8000/docs or n8n http://localhost:5678  
   Weekly report workflow → markdown under `reports/`.

6. **Quality** — `make eval`  
   Pinned fixtures score routing, tools, no invented metrics.

## Commands cheat-sheet

```bash
make up
make status
make eval
make report
# optional visual n8n:
make n8n-build && make up-n8n && make n8n-import
```

## Talking points

- Single orchestrator (ADR-004)
- Deterministic skills for math (ADR-002)
- Optional Langfuse (no-op without keys)
- Corporate-friendly: venv mounted into containers; n8n built from cached `node:20-slim`
