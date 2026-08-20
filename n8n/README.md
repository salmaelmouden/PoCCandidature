# n8n — visual automation (Phase 9)

n8n runs **with a full visual editor** in Docker Compose.

## URLs

| Service | URL |
|---------|-----|
| **n8n UI (visual)** | http://localhost:5678 |
| API (for n8n HTTP nodes) | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Streamlit | http://localhost:8501 |

## Start

```bash
make install
make up
make status
# open http://localhost:5678
```

First visit: create a local n8n owner account (stored in the `gia_n8n_data` volume).

## Import the canvas workflow

1. Open http://localhost:5678
2. **Workflows → Add workflow → Import from File**
3. Choose `n8n/workflows/weekly_growth_report.json`
4. You should see sticky notes + Manual / Schedule → HTTP → Format nodes
5. Click **Execute workflow** (Manual Trigger)

Or from the host:

```bash
make n8n-import
```

## What the workflow does

```text
Manual Trigger ─┐
                ├─→ HTTP POST gia-api:/api/reports/weekly → Format fields
Schedule Mon 9 ─┘
```

The API builds KPIs + funnel + optional orchestrator recommendations into markdown and saves under `./reports/`.

## Network note

Inside Docker, n8n calls `http://gia-api:8000` (compose service DNS).  
From the host browser, use `http://localhost:8000`.
