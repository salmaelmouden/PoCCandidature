# Plan: Phase 7 — Experimentation skill + agent

**Status:** Implemented  
**Branch:** `phase-7-experimentation`  
**Scope:** `experiment_analysis` skill, `growth_experiment_analyst_agent`, orchestrator experiment route, Streamlit Experiments page.  
**Out of scope:** Live A/B platform, Langfuse, n8n, required LLM.

## Goals

1. Deterministic experiment stats: rates, absolute/relative lift, CI for difference, two-proportion z-test.
2. Agent answers “How should we test this?” / “Did this experiment work?” from DB + optional analyst context.
3. Orchestrator routes experiment questions to the experiment agent.

## Design

### Skill `experiment_analysis`

- Pure Python (no scipy): normal approx + Wilson-friendly documented formulas.
- Inputs: control/treatment users & conversions (or rates derived).
- Outputs: rates, lift, CI, z, p-value, significant at alpha.

### Agent `growth_experiment_analyst_agent`

- Tools: list/analyze experiments via repository; optional analyst report for proposals.
- Outputs: FACT (stats) + INTERPRETATION + RECOMMENDATION (ship / iterate / design).

### Orchestrator

- New route `experiment` when question mentions experiment / A/B / significance / how to test.

## DoD

- [x] Skill + unit tests
- [x] Agent + unit tests
- [x] Orchestrator route + dashboard page
- [x] Docs updated
- [ ] Commit/push
