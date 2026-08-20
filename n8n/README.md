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

## Workflow

Import `n8n/workflows/weekly_growth_report.json` (or `make n8n-import`).

Canvas: Manual / Monday schedule → HTTP `http://gia-api:8000/api/reports/weekly` → Format.

## Fallback if build fails

- Ask IT for a mirrored n8n image, or  
- On another network: `docker pull n8nio/n8n:1.106.3 && docker save ...` then  
  `docker load` and `N8N_IMAGE=n8nio/n8n:1.106.3 make up-n8n`
