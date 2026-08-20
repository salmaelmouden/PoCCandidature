# Plan: Phase 2 — Analytics Skills

**Status:** Implemented (awaiting merge)  
**Branch:** `phase-2-analytics-skills`  
**Scope:** Deterministic skills `funnel_analysis`, `content_analysis`, `anomaly_detection`.  
**Out of scope:** Agents, Streamlit, YouTube API, experiment skill, Langfuse.

## Design

- Pure Python + Pydantic schemas (no Streamlit, no LLM).
- Skills accept structured inputs (not DB sessions) so they stay independently testable.
- Repositories remain the path to load data; later application services will glue repos → skills.
- Extra repo reads (`list_between`, `daily_metric_series`) support future glue without embedding SQL in skills.

## Skills

1. **funnel_analysis** — calculate_funnel, conversion rates, dropoffs, bottleneck, period compare
2. **content_analysis** — Content Value Score, rank, topic compare, reach/conversion gaps
3. **anomaly_detection** — z-score, IQR, % change, rolling mean deviation

## DoD

- [x] Typed schemas + README contracts
- [x] Unit tests (normal, edge, empty) — 26 passed with Phase 1 tests
- [x] Docs/phases updated
- [x] Docker Phase 1 verified (`make up` / migrate / seed on port 5434)
- [ ] Commit + push on phase-2 branch
