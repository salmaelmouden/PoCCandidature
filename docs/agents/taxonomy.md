# Agent Taxonomy

## Types

| Type | Role |
|------|------|
| Orchestrator | Coordinates agents and tools; synthesizes final answer |
| Analyst | Retrieves and interprets evidence |
| Strategist | Turns evidence into prioritized recommendations |
| Operator | Executes actions (future; not in initial set) |

## Initial agents

| Identity | Type | Question |
|----------|------|----------|
| `growth_orchestrator_agent` | Orchestrator | How should this request be routed and synthesized? |
| `growth_data_analyst_agent` | Analyst | What is happening? |
| `growth_strategist_agent` | Strategist | What should we do? |
| `growth_experiment_analyst_agent` | Analyst/Strategist hybrid for tests | How should we test this? |

Do not add agents without an ADR and a clear gap no skill can fill.

## Naming

- Identity / directory: `<domain>_<role>_agent`
- Class: `GrowthDataAnalystAgent`
- Forbidden: `agent1`, `smart_agent`, `helper_agent`, `growth_bot`, …

## Contracts

Every agent uses `docs/templates/agent-contract.md`.

## Semantic outputs

**FACT** — measured from skills/DB  
**INTERPRETATION** — reasoned from facts  
**RECOMMENDATION** — action proposal grounded in interpretation
