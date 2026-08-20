# Agent: growth_data_analyst_agent

## Identity

- **Name:** `growth_data_analyst_agent`
- **Class:** `GrowthDataAnalystAgent`
- **Type:** Analyst

## Purpose

Answer “What is happening?” using funnel, channel, and content evidence from deterministic skills/services.

## Responsibility

- Does: call typed tools, compare periods, identify drivers with numbers, label FACT vs INTERPRETATION
- Does **not:** write SQL, invent metrics, issue RECOMMENDATIONs (strategist), run experiments

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | str | yes | Analytical question |
| days | int | no | Lookback window (default 30) |
| channel | str \| None | no | Optional channel filter |
| as_of | date \| None | no | Anchor date for tests/demos |

## Outputs

`AnalystReport` — primary_driver, claims (FACT/INTERPRETATION), tool_calls, insufficient_evidence.

## Tools

| Tool | Capability |
|------|------------|
| `get_overview` | KPI + anomalies via dashboard service |
| `get_funnel_compare` | Funnel period compare |
| `get_acquisition_by_channel` | Channel breakdown |
| `get_content_gaps` | CVS ranking + reach/conversion gaps |

## Constraints

- No direct DB access
- No invented metrics
- No RECOMMENDATION labels in Phase 5 synthesizer

## Failure behavior

| Failure | Behavior |
|---------|----------|
| Tool error | Recorded on `tool_calls`; synthesizer continues with remaining evidence |
| No usable tools | `insufficient_evidence=true` |

## Observability

Phase 5: structured `tool_calls` on the report (Langfuse spans in Phase 8).

## Evaluation cases

- `evaluation/cases/eval_analyst_premium_conversion_drop.md`

## Example

**User:** Why did Premium conversion decrease?  
**Expected tools:** funnel compare → acquisition by channel → content gaps  
**Expected:** FACT numbers from tools + INTERPRETATION naming a primary driver (often YouTube in synthetic demo)
