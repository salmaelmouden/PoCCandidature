# Observability

Optional **Langfuse** tracing for the AI execution layer (ADR-006).

## Enable

1. `pip install 'growth-intelligence-ai[observability]'` (or `pip install langfuse`)
2. Set in `.env` (never commit secrets):

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

`LANGFUSE_HOST` is mapped to the SDK’s `LANGFUSE_BASE_URL`.

## Behavior

| Condition | Behavior |
|-----------|----------|
| Keys missing or `langfuse` not installed | No-op (CI/demos unaffected) |
| Keys + SDK present | Traces for orchestrator / agents |

## What is traced

- User question (explicit span input — not full function kwargs)
- Route decision and agents called
- Nested specialist spans
- Summary / errors (sanitized)

## Rules

- Never log API keys, passwords, or tokens
- Prefer structured metadata over raw dumps
- Call `flush_tracing()` after Streamlit agent runs
