---
name: developer
description: Standard development workflow for Growth Intelligence AI. Use before coding, while implementing, and after changes in this repository.
---

# Developer Skill

## Before coding

1. Inspect the repository structure and current phase.
2. Identify architecture layers involved (`docs/architecture/`, `.cursor/rules/02-architecture.mdc`).
3. Identify affected files; prefer minimal scope.
4. Inspect relevant tests and fixtures.
5. Inspect conventions (`.cursor/rules/`, `docs/conventions/`).

## While coding

- Make minimal changes; do not modify unrelated components.
- Reuse existing abstractions (skills, repositories, schemas).
- Avoid duplication.
- Use typing (Python 3.12+, Pydantic at boundaries).
- Add or update tests that assert behavior.
- Preserve public APIs unless the user explicitly requests a breaking change.
- Agents reason; skills execute; DB is source of truth.
- Never invent metrics or business data.

## After coding

1. Propose running tests (do not run without approval — see `AGENTS.md`).
2. Propose lint/type checks where available.
3. Inspect the diff for scope creep and architectural violations.
4. Identify risks (data correctness, agent contracts, security).
5. Update documentation when contracts or architecture change.

## Never

- Silently modify unrelated components.
- Put business logic in Streamlit or route handlers.
- Give agents direct DB access.
- Commit secrets.
