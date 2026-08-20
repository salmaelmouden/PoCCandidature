---
name: agent-builder
description: Create or extend runtime agents with explicit contracts, schemas, tools, evaluation, and observability. Use when adding or modifying agents under app/agents/.
---

# Agent Builder

Never create an agent if a deterministic function or skill is sufficient.
Never give an agent unrestricted DB access.

## Checklist (in order)

1. Define the responsibility (one clear question the agent answers).
2. Define what it explicitly does **not** do.
3. Define input schema (Pydantic).
4. Define output schema (Pydantic); use FACT / INTERPRETATION / RECOMMENDATION where relevant.
5. Define tools (typed; wrap skills — no arbitrary SQL).
6. Define failure modes (insufficient evidence, tool errors, timeouts).
7. Define system prompt (`prompts.py`) — no hidden CoT exposure to users.
8. Add evaluation cases under `evaluation/cases/`.
9. Add observability hooks (Langfuse-compatible spans when available).
10. Add tests (`agents/<name>/tests/`).
11. Add `README.md` (purpose, non-goals, tools, I/O, failures, examples).

## Naming

- Identity: `<domain>_<role>_agent`
- Class: PascalCase + `Agent`
- Directory: `app/agents/<agent_name>/`

## Allowed agents

Only these unless an ADR justifies a new one:

- `growth_orchestrator_agent`
- `growth_data_analyst_agent`
- `growth_strategist_agent`
- `growth_experiment_analyst_agent`

## Layout

```
agent.py  prompts.py  schemas.py  tools.py  config.py  README.md  tests/
```

## Contract template

Copy from `docs/templates/agent-contract.md`.
