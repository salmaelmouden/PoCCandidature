# n8n — visual automation (Phase 9)

n8n runs with a **full visual editor**. On many corporate networks, Docker Hub pulls fail (TLS proxy EOF), so n8n is an **optional Compose profile**.

## URLs

| Service | URL | How |
|---------|-----|-----|
| Streamlit | http://localhost:8501 | `make up` |
| API docs | http://localhost:8000/docs | `make up` |
| **n8n UI (visual)** | http://localhost:5678 | `make up-n8n` (needs local image) |

## Start core stack (works without Docker Hub for n8n)

```bash
make up
make status
```

Weekly reports still work via API / CLI:

```bash
curl -X POST "http://localhost:8000/api/reports/weekly?days=7"
# or
make report
```

## Start n8n visual UI

```bash
make up-n8n
make n8n-import
# open http://localhost:5678
```

### If `docker pull` fails (your case)

Error looks like: `TLS connect to fproxy...:8080: EOF` when resolving `n8nio/n8n`.

**Option A — load image from another machine / personal hotspot**

On a network that can reach Docker Hub:

```bash
docker pull n8nio/n8n:1.106.3
docker save n8nio/n8n:1.106.3 -o n8n-1.106.3.tar
```

Copy the tar to this laptop, then:

```bash
docker load -i n8n-1.106.3.tar
make up-n8n
make n8n-import
```

**Option B — override image** if IT mirrors n8n elsewhere:

```bash
export N8N_IMAGE=your-registry.example.com/n8nio/n8n:1.106.3
make up-n8n
```

## Import the canvas workflow

1. Open http://localhost:5678 → create owner account  
2. Or: `make n8n-import`  
3. Open **Weekly Growth Report** — sticky notes + Manual/Schedule → HTTP → Format  
4. **Execute workflow** (Manual Trigger)

## What the workflow does

```text
Manual Trigger ─┐
                ├─→ HTTP POST gia-api:/api/reports/weekly → Format fields
Schedule Mon 9 ─┘
```

Inside Docker, n8n calls `http://gia-api:8000`. From the host, use `http://localhost:8000`.
