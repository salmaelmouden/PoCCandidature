# Agent: growth_orchestrator_agent

## Identity

- **Name:** `growth_orchestrator_agent`
- **Class:** `GrowthOrchestratorAgent`
- **Type:** Orchestrator

## Purpose

Answer “How should this request be routed and synthesized?” — primary AI interface (ADR-004).

## Responsibility

- Does: classify route, call analyst and optionally strategist, merge claims + summary
- Does **not:** reimplement funnel math, invent recommendations, talk to the DB directly

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | str | yes | User question |
| days / channel / as_of | | no | Period filters |

## Outputs

`OrchestratorResponse` — route, agents_called, summary, nested analyst/strategy reports, claims.

## Tools / specialists

| Specialist | When |
|------------|------|
| `growth_data_analyst_agent` | Always |
| `growth_strategist_agent` | Action / ambiguous questions |

## Constraints

- Single orchestrator entrypoint (ADR-004)
- No invented metrics

## Failure behavior

Surfaces specialist `insufficient_evidence`; still returns structured response.

## Evaluation cases

- `evaluation/cases/eval_orchestrator_routing.md`
