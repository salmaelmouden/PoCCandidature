# Skill: report_generation

## Purpose

Build a deterministic weekly growth report (structured sections + markdown) from analytics inputs.

## Does

- `generate_weekly_report`

## Does not

- Access the database (service layer loads data)
- Call LLMs
- Send email / Slack (n8n owns delivery automation)

## Determinism

Fully deterministic for the same inputs.

## Side effects

None.
