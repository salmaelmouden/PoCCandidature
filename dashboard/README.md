# Dashboard (Phase 4)

Streamlit UI for growth metrics. **No business logic in pages** — pages call `app.services.dashboard`, which uses repositories + analytics skills.

## Run

```bash
make up && make migrate && make seed
make dashboard
```

Opens Overview plus pages: Acquisition, Content, Funnel.

## Layout

| Path | Role |
|------|------|
| `Home.py` | Executive overview |
| `pages/1_Acquisition.py` | Channel breakdown |
| `pages/2_Content.py` | CVS ranking + gaps |
| `pages/3_Funnel.py` | Stage rates + period compare |
| `ui.py` | Theme / banners / filters |
| `db.py` | DB session helper |

Synthetic / labelled data is always surfaced via the provenance banner.
