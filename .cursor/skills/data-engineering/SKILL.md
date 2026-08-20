---
name: data-engineering
description: Idempotent ingestion, validation, and ETL conventions for Growth Intelligence AI. Use when building pipelines, YouTube ingestion, synthetic data, or persistence.
---

# Data Engineering

## Rules

- Pipelines must be idempotent (safe re-runs; duplicate prevention).
- Validate external data before load (schema + business constraints).
- Handle API failures with timeouts, bounded retries, and clear errors.
- Use retries carefully (idempotent operations only; backoff).
- Log ingestion status with structured fields (source, counts, duration, outcome).
- Never hard-code credentials — env vars only.
- Separate extraction, transformation, and loading.
- Test edge cases (empty pages, rate limits, partial payloads, duplicates).
- Preserve historical data where appropriate (append metrics; do not silently overwrite history).

## YouTube ingestion (when implemented)

- Paginate; retry; timeout; validate; normalize.
- Idempotent upserts keyed by video ID + metric date where applicable.
- Env: `YOUTUBE_API_KEY` only via environment.

## Synthetic data

- Clearly labelled as synthetic.
- Never represented as Finary or any real company's private data.
- Include seasonality, anomalies, and changing conversion rates when generating fixtures.

## Persistence

- SQLAlchemy models + repository layer.
- Constraints and justified indexes.
- No agent direct SQL.
