# Security Strategy

## Secrets

- Env vars only; `.env.example` lists names, never values.
- Never commit `.env`, keys, tokens, certificates.

## Agent access

- Controlled tools only; no arbitrary SQL; no unrestricted DB.
- Validate tool inputs with Pydantic schemas.

## Data

- Sanitize external payloads before persistence.
- Synthetic demo data labelled; no private employer datasets.
- No Finary private APIs or logos.

## Observability

- Langfuse and logs must not receive secrets or PII.
