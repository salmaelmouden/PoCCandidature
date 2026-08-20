# Evaluation Case: YouTube CTA experiment

## Case ID

`eval_experiment_youtube_cta`

## Agent(s) under test

- `growth_experiment_analyst_agent`
- `experiment_analysis` skill
- Optional: `growth_orchestrator_agent` routing

## Question

```text
Did the YouTube CTA experiment work?
```

## Context

Synthetic experiment `syn_exp_youtube_cta` (control 378/4200 vs treatment 443/4180).

## Expected

- Load experiment via repository
- Absolute lift positive, significant at α=0.05
- Decision hint `ship_treatment`
- No invented metrics

## Pass / fail

**Fail** if significance or rates disagree with skill output on the same inputs.
