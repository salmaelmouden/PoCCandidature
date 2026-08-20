# Evaluation

Structure for evaluating Growth Intelligence AI agents.

## Layout

- `datasets/` — synthetic fixtures and pinned analytical snapshots
- `cases/` — human-readable evaluation cases
- `evaluators/` — scoring helpers (implemented in Phase 10)

## Dimensions

- tool_selection
- factuality
- numerical_accuracy
- recommendation_quality
- hallucination
- completeness
- latency (optional)
- cost (optional)

## Templates

- Case: `docs/templates/evaluation-case.md`
- Strategy: `docs/conventions/evaluation.md`

## Status

Phase 0: structure + example case only. No evaluator runtime yet.
