# Plan: Phase 6 — Strategist + Orchestrator

**Status:** In progress  
**Branch:** `phase-6-strategist-orchestrator`  
**Scope:** `growth_strategist_agent`, `growth_orchestrator_agent`, Streamlit Orchestrator page.  
**Out of scope:** Experiment agent (Phase 7), Langfuse (Phase 8), required LLM, n8n.

## Goals

1. Strategist answers “What should we do?” with **RECOMMENDATION** claims grounded in analyst evidence only.
2. Orchestrator is the primary AI entrypoint: routes to analyst and/or strategist and synthesizes (ADR-004).
3. Deterministic synthesizers (no LLM required for CI/demos), same pattern as Phase 5.

## Design

### Routing (`growth_orchestrator_agent`)

| Route | When | Agents |
|-------|------|--------|
| `analyst_only` | Diagnostic (“why”, bottleneck, anomalies, what changed) without action ask | Analyst |
| `analyst_then_strategist` | Action ask (“should we”, recommend, next steps, how to fix) or default ambiguous | Analyst → Strategist |

Orchestrator does **not** reimplement analytics or invent recommendations.

### Strategist

- Input: question + period filters; consumes `AnalystReport` (from tool or caller).
- Tool: `get_analyst_report` → wraps `GrowthDataAnalystAgent.run`.
- Output: prioritized recommendations + RECOMMENDATION claims; never invents metrics.
- Playbook maps primary_driver / claims to concrete growth actions (channel, funnel stage, content gap).

### UI

- New Streamlit page: Orchestrator (primary ask box).
- Analyst page stays for specialist demos.

## DoD

- [x] Agent packages + contract READMEs
- [x] Routing + strategy unit tests
- [x] Dashboard Orchestrator page
- [x] Docs/README/phases updated
- [ ] Commit/push branch
