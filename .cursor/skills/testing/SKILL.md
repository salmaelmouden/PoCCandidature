---
name: testing
description: Behavior-focused testing strategy for skills, agents, analytics, and APIs. Use when writing or reviewing tests in this repository.
---

# Testing Skill

## Goal

Assert behavior that protects correctness, contracts, and architecture — not coverage vanity.

## Cover

| Area | Examples |
|------|----------|
| Happy path | Expected funnel / content / experiment outputs |
| Edge cases | Zero views, single-day window, ties in ranking |
| Invalid input | Bad dates, negative counts, schema violations |
| Empty / missing | No videos, no acquisitions, null optional fields |
| Statistics | Conversion rates, CIs, significance thresholds |
| Tool schemas | Agent tools reject invalid args |
| Routing | Orchestrator selects the right specialist |

## Practices

- Prefer pytest; colocate component tests; use `tests/` for integration.
- Mock external network (YouTube, LLM, Langfuse).
- Label synthetic fixtures.
- Test skills deterministically (same input → same output).
- For agents: mock skills/tools; assert structured outputs and tool selection — not free-form prose equality alone.

## Anti-patterns

- Tests that only mirror implementation line-by-line
- Snapshotting unstable LLM text without evaluators
- Hitting real paid APIs in CI

Ask before running the suite (`AGENTS.md`).
