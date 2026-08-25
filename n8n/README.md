# n8n — visual automation (Phase 9)

Corporate Docker Hub pulls often fail (TLS proxy EOF). **Solution:** build a local
n8n image from your already-cached `node:20-slim` and install n8n via **npm**
(npm works with `NODE_EXTRA_CA_CERTS`).

## Quick start (recommended on this laptop)

```bash
make up                 # api + dashboard + postgres
make n8n-build          # builds gia-n8n:local (uses ~/certs/full-bundle.pem)
make up-n8n             # http://localhost:5678
make n8n-import         # load Weekly Growth Report canvas
```

Override proxy/CA if needed:

```bash
make n8n-build CORP_CA=$HOME/certs/haropa-proxy-bundle.pem \
  HTTP_PROXY=http://fproxy.havre-port.lan:8080 \
  HTTPS_PROXY=http://fproxy.havre-port.lan:8080
```

## URLs

| Service | URL |
|---------|-----|
| Streamlit | http://localhost:8501 |
| API docs | http://localhost:8000/docs |
| **n8n UI** | http://localhost:5678 |

## What `n8n-build` does

1. Copies corporate CA → `docker/n8n/certs/full-bundle.pem`
2. `docker build` **FROM node:20-slim** (already on your machine — no Hub pull for base)
3. `npm install n8n@1.106.3` inside the image (npm registry + CA)
4. Tags `gia-n8n:local`

## Workflows

Two canvases, on two different data tracks. They are never merged: one runs on the
labelled synthetic funnel, the other on the real public catalogue.

| Workflow | File | Schedule | Calls | Produces |
|---|---|---|---|---|
| Weekly Growth Report | `weekly_growth_report.json` | Monday 09:00 | `POST /api/reports/weekly` | English growth report over the **synthetic** funnel, markdown under `reports/` |
| Weekly Editorial Memo | `weekly_editorial_memo.json` | Monday 07:00 | `POST /api/memo/editorial` | French editorial memo over the **real** catalogue, markdown under `reports/` |

`make n8n-import` loads the first. Import the second from the n8n UI, or point the
same CLI at it:

```bash
docker compose --profile n8n exec -u node -w /opt/n8n n8n \
  /opt/n8n/node_modules/.bin/n8n import:workflow \
  --input=/import/weekly_editorial_memo.json
```

### Why the memo canvas has a failure branch

The memo endpoint refuses to emit a memo that fails its post-conditions — a
hand-typed figure, or funnel vocabulary outside the section that disowns it — and
returns 500 rather than a plausible-looking memo. It returns 409 when the catalogue
is too thin to write about at all.

The HTTP node is therefore set to `neverError` with the full response, so those
statuses reach an IF node instead of killing the run. The failure branch explains
which post-condition tripped. It does **not** log anything: the API already recorded
the run before responding.

### Run history

Every execution is written to `automation_runs`, successful or not, and the
dashboard's **Automatisation** page reads it. That page is the point of the table —
a job that silently stops being triggered writes no error anywhere, so "the memo
stopped arriving" would otherwise be indistinguishable from "the memo was not due".

## Fallback if build fails

- Ask IT for a mirrored n8n image, or  
- On another network: `docker pull n8nio/n8n:1.106.3 && docker save ...` then  
  `docker load` and `N8N_IMAGE=n8nio/n8n:1.106.3 make up-n8n`
