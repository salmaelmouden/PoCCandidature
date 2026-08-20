# Observability Strategy

## Target (Phase 8) — implemented

Optional Langfuse traces for:

- user question
- orchestrator decisions
- agent calls
- tool / skill calls (analyst tools)
- latency (span timing)
- errors (span failures swallowed; app continues)
- final response summary

Model identity / token usage: N/A while agents are deterministic (no LLM). Ready when LLM layer is added.

See `app/observability/` and `docs/guides/langfuse.md`.

## Rules

- Do not log secrets, API keys, or passwords.
- Do not log sensitive personal data.
- Prefer structured span attributes over raw prompt dumps when sensitive.

## Demo

High-level activity in UI (analyzed funnel / channels / content / period) — **not** chain-of-thought.
