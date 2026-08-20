# Guide: n8n visual editor + weekly report

See also [`n8n/README.md`](../../n8n/README.md).

## Why n8n here

Show interviewers a **visual** automation canvas (not only JSON): schedule → call Growth Intelligence API → materialize a weekly report.

## Prerequisites

- `make install` (venv with FastAPI + uvicorn)
- Docker

## Demo script

1. `make up` → wait until `gia-api`, `gia-n8n`, `gia-dashboard` are running (`make status`)
2. Open **http://localhost:5678** → create owner user
3. Import `n8n/workflows/weekly_growth_report.json` (or `make n8n-import`)
4. Open the workflow — confirm sticky notes and node layout
5. **Execute workflow**
6. Inspect output markdown; optional check `reports/*.md` on disk
7. Optional: open http://localhost:8000/docs and try `POST /api/reports/weekly`

## Disable schedule in demos

Leave the workflow **inactive** so only Manual Trigger runs during interviews.
