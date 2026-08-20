# Evaluation Case: Orchestrator routing

## Case ID

`eval_orchestrator_routing`

## Agent(s) under test

- `growth_orchestrator_agent`
- `growth_data_analyst_agent`
- `growth_strategist_agent`

## Questions

1. `Why did Premium conversion decrease?` → route `analyst_only`
2. `What should we do about the Premium conversion drop?` → route `analyst_then_strategist`

## Expected behavior

- Diagnostic questions call analyst only (no RECOMMENDATION claims from strategist)
- Action questions call analyst then strategist; recommendations grounded in analyst driver
- No invented metrics

## Pass / fail

**Fail** if action questions skip strategist, or diagnostic questions emit ungrounded RECOMMENDATIONs from the orchestrator itself.
