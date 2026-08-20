# Observability Strategy

## Target (Phase 8)

Langfuse traces for:

- user question
- orchestrator decisions
- agent calls
- tool / skill calls
- latency
- model identity
- token usage when available
- errors
- final response

## Rules

- Do not log secrets, API keys, or passwords.
- Do not log sensitive personal data.
- Prefer structured span attributes over raw prompt dumps when sensitive.

## Demo

High-level activity in UI (analyzed funnel / channels / content / period) — **not** chain-of-thought.
