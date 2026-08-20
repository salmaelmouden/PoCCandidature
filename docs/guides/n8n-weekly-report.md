# Guide: n8n visual editor + weekly report

See also [`n8n/README.md`](../../n8n/README.md).

## Why n8n here

Show interviewers a **visual** automation canvas (not only JSON): schedule → call Growth Intelligence API → materialize a weekly report.

## Prerequisites

- `make install` + `make up` (API must be healthy)
- Corporate CA at `~/certs/full-bundle.pem` (used by `make n8n-build`)
- **Do not** rely on `docker pull n8nio/n8n` on this network

## Demo script

1. `make up`
2. `make n8n-build`   # once — builds `gia-n8n:local` from cached `node:20-slim` + npm
3. `make up-n8n`
4. Open **http://localhost:5678** → create owner user
5. `make n8n-import`
6. Execute the **Weekly Growth Report** workflow
7. Check markdown output / `reports/*.md`

## Disable schedule in demos

Leave the workflow **inactive** so only Manual Trigger runs during interviews.
