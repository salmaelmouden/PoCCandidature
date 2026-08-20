# Plan: Phase 10 — Evaluation + polish

**Status:** Implemented  
**Branch:** `phase-10-evaluation-polish`  
**Scope:** Runnable eval suite (pytest), scoring helpers, interview demo guide, README/DoD polish.  
**Out of scope:** New agents, Langfuse cloud setup, production auth.

## Goals

1. Score agent outputs on tool_selection, hallucination, recommendation grounding, routing.
2. Pin synthetic seed/as_of in eval fixtures so CI is deterministic.
3. Document a short interview demo path (dashboard → orchestrator → n8n/report).

## DoD

- [x] `evaluation/evaluators` + pytest cases
- [x] `make eval`
- [x] Demo guide + README/phases updated
- [ ] Commit/push
