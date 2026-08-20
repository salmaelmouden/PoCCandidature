# Testing Strategy

## Principles

- Test behavior that protects metrics correctness and contracts.
- Deterministic skills get deterministic unit tests.
- Agents are tested with mocked tools (routing + schema), not live LLM flakiness in unit tests.
- No real network or secrets in default tests.

## Layers

| Layer | What | Where |
|-------|------|--------|
| Skill unit | Math, validation, edge cases | `app/skills/*/tests/` |
| Agent unit | Tool selection, output schema, failures | `app/agents/*/tests/` |
| Analytics / repos | Query semantics with synthetic fixtures | `tests/` |
| API | Contract of FastAPI endpoints | `tests/` |
| Evaluation | Quality dimensions with datasets | `evaluation/` |

## Commands (Phase 1+)

```bash
make test
# pytest
```

Ask before running (see `AGENTS.md`).
