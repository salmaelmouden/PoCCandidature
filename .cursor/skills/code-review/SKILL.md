---
name: code-review
description: Review Growth Intelligence AI changes for correctness, architecture, security, and contracts. Use when reviewing PRs, diffs, or when the user asks for a code review.
---

# Code Review

## Review for

- Correctness (especially metrics and statistics)
- Architecture boundaries
- Security (secrets, agent data access, validation)
- Maintainability and naming
- Duplication and unnecessary complexity
- Typing and error handling
- Tests (behavior coverage for the change)
- Documentation / contract updates when needed

## Explicit flag

Use **ARCHITECTURAL VIOLATION** when a change breaks:

- UI containing business logic
- Agents accessing DB directly
- Skills depending on Streamlit
- Unrestricted SQL / data access from agents
- Circular layer dependencies
- Invented metrics or fabricated evidence in agent paths

## Severity labels

- **Critical** — must fix (correctness, security, architecture)
- **Suggestion** — improve if low cost
- **Nice to have** — optional polish

## Output format

1. Summary (1–2 sentences)
2. Findings (severity + file + why + fix direction)
3. Test gaps
4. Verdict: approve / request changes
