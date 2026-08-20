# ADR-002: Why deterministic skills?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

Growth metrics (funnels, conversion, experiment stats) must be correct and repeatable. LLMs are strong at interpretation but unreliable for arithmetic and statistical rigor.

## Decision

Implement analytics and ingestion as **deterministic skills** in Python. LLMs may only interpret skill outputs, never invent numbers.

## Alternatives

| Option | Why not |
|--------|---------|
| LLM computes metrics | Hallucination risk; non-reproducible |
| SQL-only in agent prompts | Unrestricted data access; hard to test |

## Consequences

### Positive

- Testable calculations; evaluable agents
- Clear FACT vs INTERPRETATION boundary

### Negative / trade-offs

- More upfront schema/skill design

### Follow-ups

- Phase 2+: implement analytics skills with documented formulas
