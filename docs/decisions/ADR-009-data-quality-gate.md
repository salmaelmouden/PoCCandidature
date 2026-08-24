# ADR-009: What an agent emits when the data is flagged as unreliable

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** Growth Intelligence AI maintainers
- **Amends:** ADR-002 (deterministic skills), ADR-003 (controlled agent tools)

## Context

An `int()` at the `day × channel × topic` grain floored the synthetic Premium stage to
11 conversions in 60 days against a configured ~12 %. Every layer downstream then did
exactly what it was specified to do:

- `sum_funnel` aggregated the zeros faithfully.
- `calculate_funnel` computed a 100 % dropoff — arithmetically correct.
- `growth_strategist_agent` matched its playbook and emitted
  `[P0] Fix Premium leak on weakest channel`, with a paywall-and-CTA remediation plan.
- n8n shipped it every Monday.

No component was at fault under its own contract, and no component was responsible for
asking whether the number was real. The failure was structural, not local.

Three guardrails that should have caught it were silent for related reasons:

1. `test_youtube_premium_declines_in_recent_window` asserted only `current < previous`.
   The truncation produced a *sharper* decline (100 % instead of the configured 42 %),
   so the broken generator satisfied the assertion more easily than a correct one.
2. The evaluation fixtures all pinned a healthy terminal stage, so the agents had
   never been scored against a degenerate funnel.
3. Nothing in the pipeline distinguished "this stage converts badly" from "this stage
   is not being measured".

## Decision

**A stage flagged as unreliable cannot carry urgent work, and the rule is enforced in
Python, not in a prompt.**

Concretely:

1. `metric_validation` (deterministic skill) classifies implausible funnel results and
   marks the blocking ones.
2. The **application service** calls it and passes `data_warnings` into
   `StrategistQuestion`. The service, not the agent — warnings must also reach reports
   generated with `include_orchestrator=False`.
3. A **deterministic post-condition** on the agent's output withholds any
   recommendation whose `target_stage` is blocked, and inserts a P2 verification item
   in its place.
4. `insufficient_evidence` is set, and the warning that caused the substitution is
   cited in `grounded_in`.

The replacement is not a deletion. Silence reads as health, which is the failure this
exists to prevent, and `03-agents.mdc` requires an agent to state when its evidence is
insufficient.

`target_stage` is a declared field on `Recommendation` rather than something inferred
from the prose, so the gate matches recommendations to warnings without parsing English.

## Why not a prompt instruction

Because the correctness of the guardrail would then depend on the model complying with
it — unverifiable in CI, and untestable without a live LLM. ADR-002 already puts
arithmetic in deterministic Python for this reason; a rule about when a conclusion is
permitted is the same kind of object as a calculation, and belongs in the same place.
The warnings *are* also given to the agent as input context, but that is redundancy,
not the mechanism.

## Alternatives

| Option | Why not |
|--------|---------|
| Instruct the agent in `prompts.py` | Correctness depends on compliance; not testable without an LLM |
| Suppress the recommendation silently | A quiet report reads as a healthy one — the exact failure mode |
| Let the skill refuse to emit a `FunnelResult` | Conflates measuring with judging; `funnel_analysis` is right to report what it was given |
| Repair the data in the validator | A validator that edits its input hides the fault instead of surfacing it |

## Consequences

### Positive

- The `P0`-on-an-artefact class of failure is unreachable, whatever caused the artefact.
- The guardrail is testable with no LLM in the loop.
- Data faults become visible to the reader instead of being narrated over.

### Negative / trade-offs

- Thresholds are a judgment call. `MIN_SIGNIFICANT_UPSTREAM = 100` will occasionally
  block a genuinely empty stage on a real low-traffic slice.
- Agents can no longer be read in isolation: some of their output shape is decided
  after they run.

### Follow-ups

- Surface warnings at the top of the weekly report and the editorial memo (W3), never
  as a footnote.
- Keep `eval_strategist_degenerate_funnel` in the suite — it is the regression case,
  and it is the one the previous fixtures could not express.
