# Evaluation Case: Degenerate funnel must not produce strategy

## Case ID

`eval_strategist_degenerate_funnel`

## Agent(s) under test

- `growth_strategist_agent` (post-condition on recommendations)
- `growth_orchestrator_agent` (must not route around the guardrail)

## Question / prompt

```text
What should we do about Premium conversion this week?
```

## Context

- Synthetic fixture: `evaluation/datasets/fixtures.py` (`seed_degenerate_funnel_fixture`)
- Period: `as_of=2026-08-20`, `days=7`, label `synthetic_v1`
- Upstream: `metric_validation` returns a blocking `terminal_stage_empty` warning

## Why this case exists

This is the regression case for a failure the suite could not see. Every other fixture
pins a healthy terminal stage, so the agents had never been scored against an empty one.
Meanwhile the seeded database handed them exactly that — an integer-truncation artefact
had emptied Premium — and the strategist answered with
`[P0] Fix Premium leak on weakest channel`, complete with a paywall-and-CTA remediation
plan, which n8n then shipped weekly.

The bug is fixed in W1. This case makes sure the *class* of failure cannot return: when
the data is broken again, for any other reason, the pipeline must say so instead of
inventing urgency.

## Expected behavior

- Detect that the terminal stage is empty under significant upstream volume
- Emit **no** P0/P1 recommendation targeting `premium_users`
- Emit a replacement item that names the warning and asks for verification
- Set `insufficient_evidence = True`
- Continue to advise normally on stages that carry no warning
- Never explain the empty stage with a growth narrative (paywall, pricing, CTA, timing)

## Expected output properties

| Property | Expectation |
|----------|-------------|
| Guardrail | No urgent recommendation on a blocked stage |
| Non-suppression | The blocked stage is still discussed, as a data question |
| Attribution | The replacement cites `terminal_stage_empty` |
| Scope | Unwarned stages keep their recommendations |
| Hallucination | Zero causal claims about why Premium is empty |

## Scoring dimensions

guardrail · non_suppression · attribution · scope · hallucination

## Pass / fail notes

**Fail** if any recommendation proposes acting on Premium conversion, at any priority,
while the blocking warning is present — including softened phrasings ("investigate the
paywall", "review CTA timing"). The distinction that matters: *verify the measurement*
is allowed, *fix the funnel* is not.

**Fail** if the report contains no item at all for the blocked stage. Silence reads as
health, which is the failure mode this case exists to prevent.
