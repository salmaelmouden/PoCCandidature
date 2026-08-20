---
name: documentation
description: Write and update project documentation, ADRs, agent/skill READMEs, and conventions. Use when documenting architecture, decisions, or component contracts.
---

# Documentation Skill

## Document

- purpose
- architecture
- decisions (ADRs)
- usage
- limitations
- examples

## Avoid

- Obvious implementation narration ("imports X then calls Y")
- Duplicating code that the types already express
- Stale promises of features not yet in the current phase

## When to update

- New agent or skill → README + contract
- Architectural choice → ADR
- Naming / workflow change → `docs/conventions/`
- Public behavior change → README / API docs

## Templates

- Agent: `docs/templates/agent-contract.md` + agent README
- Skill: `docs/templates/skill-contract.md` + skill README
- ADR: `docs/templates/adr.md`
- Evaluation case: `docs/templates/evaluation-case.md`

## Style

Clear, short, actionable. Link rather than copy. Prefer diagrams only when they clarify structure.
