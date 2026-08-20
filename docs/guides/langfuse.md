# Langfuse setup (Phase 8)

Optional observability for orchestrator / agents (ADR-006). The app runs fully without Langfuse.

## 1. Install SDK

```bash
. .venv/bin/activate
pip install '.[observability]'
# or: pip install langfuse
```

## 2. Configure `.env`

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Keys: Langfuse Cloud → project → **Settings → API Keys**.  
US region host: `https://us.cloud.langfuse.com`.

## 3. Run a traced question

```bash
make up
# Orchestrator page → ask a question → flush happens automatically
```

Open the Langfuse **Traces** view. Expect nested spans: orchestrator → specialist → tools.

## Safety

- Secrets/PII are not logged; metadata is sanitized.
- Span **input** is the user question only (not full Python kwargs).
- Missing keys or missing package → silent no-op.
