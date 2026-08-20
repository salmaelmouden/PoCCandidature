# Skill Contract Template

Copy into `app/skills/<skill_name>/README.md` (schemas in `schemas.py`).

## Identity

- **Name:** `<domain>_<capability>`
- **Module:** `app/skills/<skill_name>/`

## Purpose

One sentence.

## Responsibility

- Does:
- Does **not**:

## Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| | | | |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| | | |

## Determinism

- [ ] Fully deterministic for the same inputs
- [ ] Partially deterministic (note external I/O)

## Side effects

None | Reads DB via repository | Writes DB | Calls external API | Filesystem

Describe precisely:

## Error handling

| Condition | Error / behavior |
|-----------|------------------|
| Invalid input | |
| Empty data | |
| Upstream failure | |

## Formulas / algorithms

Document any score or statistical method here (required for ranking/scoring skills).

## Tests

- Location: `app/skills/<skill_name>/tests/`
- Key cases:

## Example

```text
Input: …
Output: …
```
