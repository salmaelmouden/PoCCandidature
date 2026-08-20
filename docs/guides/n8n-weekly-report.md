# Guide: n8n visual editor + weekly report

See also [`n8n/README.md`](../../n8n/README.md).

## Why n8n here

Show interviewers a **visual** automation canvas (not only JSON): schedule → call Growth Intelligence API → materialize a weekly report.

## Prerequisites

- `make install` (venv with FastAPI + uvicorn)
- Docker
- **n8n image available locally** if Docker Hub is blocked by corporate TLS proxy  
  (see [`n8n/README.md`](../../n8n/README.md) — `docker load` workaround)

## Demo script

1. `make up` → core stack (postgres, api, dashboard) — **does not pull n8n**
2. Optional: load `n8nio/n8n:1.106.3` then `make up-n8n`
3. Open **http://localhost:5678** → create owner user
4. `make n8n-import` (or Import from File → `n8n/workflows/weekly_growth_report.json`)
5. **Execute workflow**
6. Inspect markdown; check `reports/*.md`
7. Without n8n: `make report` or http://localhost:8000/docs

## Disable schedule in demos

Leave the workflow **inactive** so only Manual Trigger runs during interviews.
