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

## Project commands

```bash
make up              # Docker: postgres + migrate + seed + dashboard (+ api)
make status          # docker compose ps -a
make logs            # follow container logs
make down            # stop stack
make install         # local .venv
make migrate         # local alembic
make seed            # local seed
make ingest-youtube  # YouTube Data API ingest (needs API key)
make classify        # LLM (or fallback) topic + hook labels
make public-report   # public-signal evidence table (CLI)
make dashboard       # local Streamlit
make api             # local FastAPI
make report          # weekly markdown report
make test            # pytest -q
make eval            # agent evaluation suite
make lint            # ruff
```

Preferred path: **`make up`** then open http://localhost:8501 and use **`make status`** to see what is running.

## Hard stops

- Do not read or commit secrets (`.env`, keys, tokens).
- Do not patch `vendor/` / `node_modules/` / generated build output.
- Do not expand scope without an explicit ask.
- Do not invent business metrics or present synthetic data as real company data.
- No Finary private APIs, logos, or proprietary datasets.
- Never infer signups or conversion from public YouTube stats.
