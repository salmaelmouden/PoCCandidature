# Agent: growth_strategist_agent

## Identity

- **Name:** `growth_strategist_agent`
- **Class:** `GrowthStrategistAgent`
- **Type:** Strategist

## Purpose

Answer “What should we do?” with prioritized recommendations grounded in analyst evidence.

## Responsibility

- Does: consume `AnalystReport`, emit RECOMMENDATION claims with priority, never invent metrics
- Does **not:** write SQL, re-run funnel math itself, design full experiments (Phase 7), skip the analyst

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | str | yes | Strategy question |
| days / channel / as_of | | no | Period filters |
| analyst_report | AnalystReport \| None | no | Skip re-run when orchestrator already has it |

## Outputs

`StrategyReport` — recommendations (P0–P2), claims (FACT + RECOMMENDATION), tool_calls.

## Tools

| Tool | Capability |
|------|------------|
| `get_analyst_report` | Wraps `GrowthDataAnalystAgent.run` |

## Constraints

- No direct DB access
- No invented metrics
- Recommendations must cite analyst primary_driver / FACT numbers

## Failure behavior

| Failure | Behavior |
|---------|----------|
| Analyst fails / insufficient | `insufficient_evidence=true`, no recommendations |

## Evaluation cases

- `evaluation/cases/eval_strategist_premium_actions.md`
- Orchestrator routing: `evaluation/cases/eval_orchestrator_routing.md`
