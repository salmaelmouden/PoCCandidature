# Agent Contract Template

Copy into `app/agents/<agent_name>/README.md` (and keep schemas in `schemas.py`).

## Identity

- **Name:** `<domain>_<role>_agent`
- **Class:** `<Domain><Role>Agent`
- **Type:** Orchestrator | Analyst | Strategist | Operator

## Purpose

One sentence: the question this agent answers.

## Responsibility

- Does:
- Does **not**:

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| | | | |

Link to Pydantic model: `schemas.py`

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| | | |

Semantic labels used: FACT / INTERPRETATION / RECOMMENDATION

## Tools

| Tool | Skill / capability | Purpose |
|------|--------------------|---------|
| | | |

## Constraints

- No direct DB access
- No invented metrics
- …

## Failure behavior

| Failure | Behavior |
|---------|----------|
| Insufficient evidence | State insufficiency; do not invent |
| Tool error | Surface structured error; degrade gracefully |
| Timeout | |

## Observability

- Traces / spans to record:
- Fields never to log (secrets, PII):

## Evaluation cases

- Path under `evaluation/cases/`:
- Success criteria:

## Example interactions

### Example 1

**User:**  
**Expected tool use:**  
**Expected output shape:**  
