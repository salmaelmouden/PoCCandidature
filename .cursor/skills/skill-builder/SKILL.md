---
name: skill-builder
description: Create or extend deterministic runtime skills with typed I/O, tests, and documentation. Use when adding or modifying skills under app/skills/.
---

# Skill Builder

A skill is a reusable capability — small, typed, testable, deterministic whenever possible.

## Checklist

1. One responsibility; name it `<domain>_<capability>`.
2. Define typed inputs (`schemas.py`).
3. Define typed outputs (`schemas.py`).
4. Implement in `skill.py` (Python for calculations; no LLM for math).
5. Handle errors explicitly (validation, empty data, external failures).
6. Avoid hidden side effects; document any persistence or I/O.
7. Add independent tests (`skills/<name>/tests/`).
8. Add `README.md` (purpose, formula if any, I/O, limitations, examples).
9. Fill contract from `docs/templates/skill-contract.md`.

## Runtime skills

`youtube_ingestion` · `funnel_analysis` · `content_analysis` · `anomaly_detection` · `experiment_analysis` · `report_generation`

## Must

- Independently testable without Streamlit
- Explicit schemas at boundaries
- Documented formulas for any score (e.g. Content Value Score)

## Must not

- Depend on UI
- Bypass repository layer for DB writes
- Invent or hard-code production credentials
