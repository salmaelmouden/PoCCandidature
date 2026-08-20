# ADR-001: Why PostgreSQL?

- **Status:** Accepted (foundation)
- **Date:** 2026-08-20
- **Deciders:** Growth Intelligence AI maintainers

## Context

We need a durable source of truth for videos, daily metrics, acquisition events, users, experiments, and analytics snapshots. The system must support relational constraints, idempotent ingestion, and clear repository encapsulation.

## Decision

Use **PostgreSQL** as the primary datastore, accessed via SQLAlchemy repositories.

## Alternatives

| Option | Why not |
|--------|---------|
| SQLite only | Fine for demos; weaker for concurrent workers, ops realism |
| Document store | Funnel/relational integrity is a poor fit |
| Warehouse-only (BigQuery etc.) | Overkill for MVP; adds cost/complexity |

## Consequences

### Positive

- Realistic fintech-adjacent stack for interviews
- Constraints, indexes, transactions
- Clear path for Docker Compose

### Negative / trade-offs

- Requires local/docker Postgres vs zero-deps SQLite

### Follow-ups

- Phase 1: models, repositories, synthetic seed
