# Interview / portfolio demo script

~12–14 minutes. Stack: `make up` (optional `make up-n8n` after `make n8n-build`).

## Narrative

> Two honest tracks: **labelled synthetic funnel** (Premium / experiments) and **public
> YouTube catalogue** (reach / engagement / topics — never inferred signups).  
> Agents reason; skills compute; Postgres is source of truth. LLM labels text only (ADR-008).

## Walkthrough

### Track 0 — The landing page (30 seconds)

0. **En bref** — http://localhost:8501  
   Four readings of the real catalogue and the move each implies, plus the
   guardrail story. Every number is derived from the same live report the full
   catalogue page reads, so the summary cannot drift after an ingest. A visitor
   who reads nothing else still leaves with a finding **and** its provenance.

### Track A — Synthetic funnel (decision support)

1. **Synthèse** — http://localhost:8501  
   KPIs with sparklines, daily traffic with flagged days, funnel shape and its
   leak point. Point at the `synthetic_v1` provenance banner.

2. **Analyste** — “Why did Premium conversion decrease?”  
   FACT vs INTERPRETATION as labelled cards, tool log, primary driver.

3. **Orchestrateur** — same question vs “What should we do about Premium?”  
   Route changes: analyst-only → analyst + strategist recommendations.

4. **Expérimentations** — “Did the YouTube CTA experiment work?”  
   Decision hint from the deterministic stats skill.

5. **Automation** — http://localhost:8000/docs or n8n http://localhost:5678  
   Weekly report → markdown under `reports/`.

### Track B — Real public catalogue (measurement honesty)

6. **Catalogue public** — sidebar, section “Signal public”  
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
- Chart form is chosen per job, and the palette was run through a colour-vision
  validator rather than picked by eye — every sub-3:1 colour ships a table twin
- Corporate-friendly: venv mounted into containers; n8n from cached `node:20-slim`
