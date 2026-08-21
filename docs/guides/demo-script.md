# Interview / portfolio demo script

~12–14 minutes. Stack: `make up` (optional `make up-n8n` after `make n8n-build`).

## Narrative

> Two honest tracks: **labelled synthetic funnel** (Premium / experiments) and **public
> YouTube catalogue** (reach / engagement / topics — never inferred signups).  
> Agents reason; skills compute; Postgres is source of truth. LLM labels text only (ADR-008).

## Walkthrough

### Track A — Synthetic funnel (decision support)

1. **Overview** — http://localhost:8501  
   KPIs, bottleneck, anomalies. Point at `synthetic_v1` provenance banner.

2. **Analyst** — “Why did Premium conversion decrease?”  
   FACT vs INTERPRETATION, tool calls, primary driver.

3. **Orchestrator** — same question vs “What should we do about Premium?”  
   Route changes: analyst-only → analyst + strategist recommendations.

4. **Experiments** — “Did the YouTube CTA experiment work?”  
   Decision hint from the deterministic stats skill.

5. **Automation** — http://localhost:8000/docs or n8n http://localhost:5678  
   Weekly report → markdown under `reports/`.

### Track B — Real public catalogue (measurement honesty)

6. **Catalogue public** — sidebar page  
   Live reach/engagement by topic & hook × format, curated readings from the report.  
   Static deep-dive: `docs/insights/catalogue-finary.html`.

7. **Quality** — `make eval`  
   Pinned fixtures score routing, tools, no invented metrics.

## Commands cheat-sheet

```bash
make up
make status
make eval
make report
make public-report   # CLI evidence table
# optional visual n8n:
make n8n-build && make up-n8n && make n8n-import
```

## Talking points

- Single orchestrator (ADR-004)
- Deterministic skills for math (ADR-002); LLM only labels titles (ADR-008)
- Cohort-normalised reach — raw views are confounded by channel growth
- Always report per format (catalogue is ~52% Shorts)
- Optional Langfuse (no-op without keys)
- Corporate-friendly: venv mounted into containers; n8n from cached `node:20-slim`
