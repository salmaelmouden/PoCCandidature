# Evaluation Case Template

Save under `evaluation/cases/<case_id>.md` (and optional JSON fixture under `evaluation/datasets/`).

## Case ID

`eval_<area>_<short_name>`

## Agent(s) under test

- 

## Question / prompt

```text

```

## Context

Period, synthetic dataset version, constraints:

## Expected behavior

- Tool selection:
- Evidence retrieval:
- Must use actual numbers from tools/skills:
- Must not invent metrics:
- Completeness criteria:

## Expected output properties

| Property | Expectation |
|----------|-------------|
| Factuality | Claims trace to tool results |
| Numerical accuracy | Matches skill outputs within tolerance |
| Recommendation quality | (if applicable) grounded in findings |
| Hallucination | Zero invented metrics |
| Structure | Matches output schema |

## Scoring dimensions

- tool_selection
- factuality
- numerical_accuracy
- recommendation_quality
- hallucination
- completeness
- latency (optional)
- cost (optional)

## Pass / fail notes

-
