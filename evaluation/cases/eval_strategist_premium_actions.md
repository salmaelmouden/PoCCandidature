# Evaluation Case: Strategist Premium actions

## Case ID

`eval_strategist_premium_actions`

## Agent(s) under test

- `growth_strategist_agent` (with analyst tool)

## Question / prompt

```text
What should we do about the Premium conversion drop?
```

## Expected behavior

- Calls `get_analyst_report` (or uses provided AnalystReport)
- Emits prioritized RECOMMENDATION claims
- Grounds actions in primary_driver / FACT numbers
- Does not invent metrics or full experiment designs

## Pass / fail

**Fail** if recommendations cite numbers absent from the analyst report, or if RECOMMENDATION is emitted with insufficient analyst evidence.
