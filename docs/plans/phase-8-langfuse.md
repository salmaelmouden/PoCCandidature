# Plan: Phase 8 — Langfuse observability

**Status:** Implemented  
**Branch:** `phase-8-langfuse`  
**Scope:** Optional Langfuse tracing for orchestrator/agents/tools; never required for CI.  
**Out of scope:** Self-hosted Langfuse compose, n8n, evaluation runners, LLM generations (still deterministic agents).

## Goals

1. Traces when `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` are set and `langfuse` is installed.
2. Full no-op otherwise (tests/CI/demos without keys).
3. Never log secrets or PII; sanitize metadata; set explicit span input (question only).

## Design

- `app/observability/` — `is_tracing_enabled`, `observation` context manager, `flush`, `sanitize`
- Instrument `GrowthOrchestratorAgent.run` (root) + nested specialist spans
- Instrument specialist `run` methods for standalone dashboard pages
- Env: keep `LANGFUSE_HOST` (alias → `LANGFUSE_BASE_URL` for SDK)

## DoD

- [x] Observability module + unit tests (noop path)
- [x] Agents instrumented
- [x] Docs / `.env.example` / optional dep
- [ ] Commit/push
