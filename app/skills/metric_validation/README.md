# Skill: metric_validation

## Identity

- **Name:** `metric_validation`
- **Module:** `app/skills/metric_validation/`

## Purpose

Decide whether a funnel result can be read as a growth finding at all, before anything
downstream interprets it.

## Why it exists

An `int()` applied at the `day × channel × topic` grain floored the Premium stage to
11 conversions in 60 days against a configured ~12 % (`app/db/synthetic.py`, fixed in
Phase 16 / W1). `calculate_funnel` correctly reported a 100 % dropoff on that stage —
the arithmetic was right, the input was not. The strategist then produced:

```text
[P0] Fix Premium leak on weakest channel
     Audit signup→activation→Premium path: landing message match, paywall timing,
     and CTA clarity. Compare Premium rate to the best channel before changing spend.
```

A confident, urgent, fully-reasoned remediation plan for a rounding artefact — shipped
weekly by n8n. Every layer behaved as specified; none of them was responsible for
asking whether the number was real. This skill is that layer.

## Responsibility

- Does: flag stages whose emptiness is implausible given upstream volume, and say
  which of those flags forbid downstream urgency.
- Does **not**: access the DB, call an LLM, repair data, interpret, or decide what to
  do about the fault.

## Boundary

Deterministic Python, per ADR-002. The rule is deliberately not a prompt instruction:
an agent asked politely not to over-interpret will over-interpret. What an agent must
emit in place of a withheld recommendation is ADR-009.

## Rules

| Condition | Code | Blocking |
|-----------|------|----------|
| Final stage empty, upstream ≥ `MIN_SIGNIFICANT_UPSTREAM` | `terminal_stage_empty` | yes |
| Mid-funnel stage empty, upstream ≥ `MIN_SIGNIFICANT_UPSTREAM` | `impossible_dropoff` | yes |
| Any stage empty, upstream below threshold | `cohort_too_small` | no |
| Stage empty because upstream is also empty | — | not reported |

`MIN_SIGNIFICANT_UPSTREAM = 100`. Below it, an empty stage is ordinary smallness — 0
Premium out of 12 activations is a slow week, not a broken pipeline. Blocking there
would fire on every low-traffic slice and train its readers to skip the warnings,
which costs more than the bug it prevents.

## Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `result` | `FunnelResult` | yes | produced by `funnel_analysis` |
| `min_significant_upstream` | `int` | no | defaults to `MIN_SIGNIFICANT_UPSTREAM` |

## Outputs

`ValidationResult` — `warnings: list[DataWarning]`, plus derived `has_blocking` and
`blocking_stages`. Each `DataWarning` carries `code`, `stage`, `upstream_stage`,
`blocking`, a formatted `message`, and the `numbers` that justify it. The numbers
travel with the warning on purpose: a warning a reader cannot check is a warning a
reader will dismiss.

## Determinism

- [x] Fully deterministic for the same inputs
- [ ] Partially deterministic

No I/O, no clock, no randomness.

## Side effects

None. The application service calls it and passes the result into agent input — not
the agent, so that warnings still surface on reports generated with no agent in the
loop (`include_orchestrator=False`).

## Error handling

| Condition | Behavior |
|-----------|----------|
| Empty funnel (all zeros) | No warnings — nothing to distrust |
| Upstream zero, stage zero | Not reported; arithmetic, not a fault |
| Counts increasing down the funnel | Rejected upstream by `FunnelCounts` |

## Tests

- Location: `app/skills/metric_validation/tests/`
- Key cases: healthy funnel stays silent, the historical 566/0 case blocks, thin
  volume does not block, exact threshold boundary, mid-funnel collapse, purity, and
  every code carrying a human-readable sentence.
- Regression case at the agent layer: `evaluation/cases/eval_strategist_degenerate_funnel.md`.
