# Agent workflow

Default delivery cycle:

**Plan → @critic → @test-writer → implement (red→green)**

- Plans: `docs/plans/`
- Critic is read-only: `PASS` or `CHANGES REQUESTED` only.
- Test-writer writes tests from a passed plan; no product code.
- Ask before running tests, builds, migrations, or network commands.

## Project

**Growth Intelligence AI** — see `README.md` and `.cursor/rules/00-project.mdc`.

Phase discipline: do not implement later-phase application code until the current phase is approved.

## Project commands (Phase 1+)

```bash
# tests
make test

# lint / typecheck
make lint
```

Until the Makefile targets exist, do not invent alternatives — ask.

## Hard stops

- Do not read or commit secrets (`.env`, keys, tokens).
- Do not patch `vendor/` / `node_modules/` / generated build output.
- Do not expand scope without an explicit ask.
- Do not invent business metrics or present synthetic data as real company data.
- No Finary private APIs, logos, or proprietary datasets.
