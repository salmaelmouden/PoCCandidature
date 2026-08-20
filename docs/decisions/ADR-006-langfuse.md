# ADR-006: Why Langfuse?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

AI-native systems need observability: which agent ran, which tools were called, latency, errors, and (when available) token usage — without logging secrets or PII.

## Decision

Use **Langfuse** to observe the AI execution layer (orchestrator, agents, tools, final responses).

## Alternatives

| Option | Why not |
|--------|---------|
| Ad-hoc logs only | Weak trace UX for demos/interviews |
| Vendor lock into one LLM console | Less portable across providers |

## Consequences

### Positive

- Demo-friendly traces; debugging agent routing

### Negative / trade-offs

- Extra infra/env configuration (Phase 8)

### Follow-ups

- Phase 8: instrumentation; never log secrets/PII
