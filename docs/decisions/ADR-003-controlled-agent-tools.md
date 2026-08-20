# ADR-003: Why controlled agent tools?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

Agents need evidence from the system but must not become an unrestricted SQL console or secret-exfiltrating process.

## Decision

Agents may only call **explicit, schema-validated tools** that wrap skills/repositories. No arbitrary SQL. No direct DB sessions in agent code.

## Alternatives

| Option | Why not |
|--------|---------|
| Free-form SQL tool | Security + correctness risk |
| Embed all data in the prompt | Doesn't scale; leakage risk |

## Consequences

### Positive

- Auditable tool traces; safer demos
- Aligns with Langfuse observability

### Negative / trade-offs

- New questions may require new tools/skills

### Follow-ups

- Tool schemas per agent in Phase 5+
