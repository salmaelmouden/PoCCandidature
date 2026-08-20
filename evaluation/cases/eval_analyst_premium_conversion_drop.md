# Evaluation Case: Premium conversion decrease

## Case ID

`eval_analyst_premium_conversion_drop`

## Agent(s) under test

- `growth_orchestrator_agent` (routing)
- `growth_data_analyst_agent` (evidence)
- Optional handoff: `growth_strategist_agent`, `growth_experiment_analyst_agent`

## Question / prompt

```text
Why did Premium conversion decrease?
```

## Context

- Synthetic fixture: `evaluation/datasets/fixtures.py` (`seed_premium_drop_fixture`)
- Period: `as_of=2026-08-20`, `days=7`, label `synthetic_v1`

## Expected behavior

- Retrieve funnel metrics for the relevant period
- Compare with the previous period
- Inspect channel performance
- Inspect content/topic drivers
- Identify primary driver using **actual numbers** from tools
- Avoid invented metrics
- Explain evidence (FACT vs INTERPRETATION)
- Orchestrator may request next action / experiment via specialists — analyst alone must not invent strategy numbers

## Expected output properties

| Property | Expectation |
|----------|-------------|
| Factuality | Claims trace to tool/skill results |
| Numerical accuracy | Matches skill outputs |
| Hallucination | Zero invented metrics |
| Completeness | Period compare + driver identification |

## Scoring dimensions

tool_selection · factuality · numerical_accuracy · hallucination · completeness

## Pass / fail notes

**Fail** if any numeric claim cannot be traced to a tool result.
