# Dashboard (Phase 4)

Streamlit UI. **No business logic in pages** — call `app.services.dashboard`.

## Docker (recommended)

```bash
make install   # once
make up
make status    # what's running vs exited
# http://localhost:8501
```

| Container | Expected |
|-----------|----------|
| `gia-postgres` | running (healthy) |
| `gia-migrate` | exited (0) |
| `gia-seed` | exited (0) |
| `gia-dashboard` | running → :8501 |

## Layout

| Path | Role |
|------|------|
| `Home.py` | Overview |
| `pages/1_Acquisition.py` | Channel breakdown |
| `pages/2_Content.py` | CVS + gaps |
| `pages/3_Funnel.py` | Funnel rates |
| `pages/4_Analyst.py` | Data analyst agent UI |
| `ui.py` / `db.py` | Presentation helpers |
