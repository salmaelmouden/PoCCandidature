# Evaluation

Runnable evaluation for Growth Intelligence AI agents (Phase 10).

## Layout

- `datasets/` — pinned fixtures (`fixtures.py`, as_of `2026-08-20`)
- `cases/` — human-readable case specs
- `evaluators/` — scoring helpers
- `tests/` — pytest suite (`make eval`)

## Dimensions

- tool_selection
- factuality
- numerical_accuracy
- recommendation_quality
- hallucination
- completeness

## Run

```bash
make eval
# or: pytest -q evaluation/tests
```

## Cases

| Case ID | Focus |
|---------|--------|
| `eval_analyst_premium_conversion_drop` | Tools + FACT + YouTube driver |
| `eval_orchestrator_routing` | analyst / strategist / experiment routes |
| `eval_strategist_premium_actions` | Grounded RECOMMENDATIONs |
| `eval_experiment_youtube_cta` | `ship_treatment` on synthetic CTA |

## Templates

- Case: `docs/templates/evaluation-case.md`
- Strategy: `docs/conventions/evaluation.md`
- Demo: `docs/guides/demo-script.md`
