# ADR-005: Why Streamlit?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

We need a fast path to a clean internal-product dashboard and chat UI for demos, without building a full frontend stack in the MVP.

## Decision

Use **Streamlit** for the dashboard and AI analyst chat. Business logic stays out of pages — pages call API/services/skills only.

## Alternatives

| Option | Why not (for MVP) |
|--------|-------------------|
| React SPA | Higher cost before core AI system exists |
| Jupyter only | Weak product feel for interviews |

## Consequences

### Positive

- Rapid UI; good enough for 3–5 min demo

### Negative / trade-offs

- Must enforce "no business logic in UI" via reviews/rules

### Follow-ups

- Phase 4: pages Overview, Acquisition, Content, Funnel; Phase 5+: AI chat
