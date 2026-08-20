# Development Architecture

The development system is **not** part of the runtime application. It makes AI-assisted development consistent.

## Cursor rules (`.cursor/rules/`)

| File | Concern |
|------|---------|
| `00-project.mdc` | Constitution / mission |
| `01-python.mdc` | Python conventions |
| `02-architecture.mdc` | Layer boundaries |
| `03-agents.mdc` | Runtime agents |
| `04-skills.mdc` | Runtime skills |
| `05-testing.mdc` | Tests |
| `06-security.mdc` | Secrets & access |
| `07-documentation.mdc` | Docs |
| `08-git.mdc` | Commits |
| `critic.mdc` / `test-writer.mdc` | Plan → test workflow |
| `command-execution.mdc` | Ask before heavy commands |
| `secrets.mdc` / `vendor-and-generated.mdc` | Hard stops |

## Cursor skills (`.cursor/skills/`)

| Skill | When |
|-------|------|
| `developer` | Default implementation workflow |
| `agent-builder` | Creating runtime agents |
| `skill-builder` | Creating runtime skills |
| `data-engineering` | Pipelines / ingestion |
| `testing` | Writing tests |
| `code-review` | Reviews |
| `documentation` | Docs / ADRs |

## Delivery cycle

**Plan → @critic → @test-writer → implement (red→green)**

Plans live under `docs/plans/`.
