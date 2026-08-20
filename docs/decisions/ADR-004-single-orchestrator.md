# ADR-004: Why a single orchestrator?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

User questions often span analysis, strategy, and experimentation. Multiple entry agents create inconsistent routing and duplicated logic.

## Decision

Expose **`growth_orchestrator_agent`** as the primary AI interface. It routes to specialists and synthesizes; it does not reimplement specialist logic.

## Alternatives

| Option | Why not |
|--------|---------|
| User picks agent in UI | Poor UX; leaks architecture |
| One mega-agent | Hard to evaluate; muddy responsibilities |

## Consequences

### Positive

- Clear demo narrative; evaluable routing
- Specialist agents stay focused

### Negative / trade-offs

- Orchestrator becomes a critical path (must be tested)

### Follow-ups

- Phase 6: orchestrator + routing tests/evals
