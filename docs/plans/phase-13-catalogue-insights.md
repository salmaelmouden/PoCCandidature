# Plan: Phase 13 — Catalogue insights + demo surface

**Status:** Implemented  
**Branch:** `phase-13-catalogue-insights`  
**Scope:** Curated findings from public-signal evidence, Streamlit page, docs/demo sync, merge hygiene.  
**Out of scope:** New agents, signup inference, scheduled ingest.

## Why

Phases 11–12 produce classifications and an evidence table via CLI only. Interview demos still stop at the synthetic funnel agents. This phase closes the loop: live tables in Streamlit + three solid findings (human judgment) + a coherent `main`.

## Flow

```text
public_signal_analysis report (facts)
        → Streamlit Public Signals page (live tables + freshness)
        → curated findings (INTERPRETATION, grounded in table numbers)
        → docs/insights/catalogue-finary.html (full narrative artifact)
```

## Decisions

- **Findings stay human-authored.** The skill emits facts; selecting which contradiction matters is growth judgment (same boundary as Phase 12).
- **English in Streamlit, French HTML narrative** — dashboard language matches the rest of the app; the HTML is the portfolio deep-dive.
- **No agent wiring yet** — avoid inventing public→signup bridges. Optional later.

## DoD

- [x] `docs/insights/` committed (HTML + README)
- [x] Streamlit **Catalogue public** page: freshness, live tables/charts, readings
- [x] English finding summaries module + unit tests
- [x] Demo script + phases.md + README + AGENTS.md synced
- [x] Commit; merge into `main`; push when SSH allows
