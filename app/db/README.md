# Database layer

PostgreSQL is the source of truth. Access goes through repositories — agents must not run SQL.

## Layout

| Module | Role |
|--------|------|
| `models.py` | SQLAlchemy 2.0 ORM models |
| `repositories.py` | Typed persistence API |
| `synthetic.py` | Labelled synthetic dataset generator |
| `loader.py` | Idempotent load of synthetic data |
| `session.py` | Engine / session helpers |
| `constants.py` | Channels, topics, funnel stages |

## Synthetic data

All seed data is **synthetic** (`is_synthetic=true`, `dataset_label=synthetic_v1`).  
Titles/descriptions are prefixed/labelled. Never present as real fintech company data.

## Commands

```bash
make up        # Postgres
make migrate   # Alembic
make seed      # Idempotent synthetic load
```
