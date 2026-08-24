"""
metric_validation — is this funnel result a finding, or a symptom of broken data?

The pipeline could not tell the difference. An integer-truncation artefact emptied
the Premium stage, `calculate_funnel` reported a 100 % dropoff, and the strategist
turned that into `[P0] Fix Premium leak on weakest channel` with a paywall-and-CTA
remediation plan for a phenomenon that never happened. n8n shipped it weekly.

Per ADR-002 the rule lives here, in deterministic Python, rather than in a prompt:
an agent asked politely not to over-interpret will over-interpret.
"""

from __future__ import annotations

from itertools import pairwise

from app.skills.funnel_analysis.schemas import FUNNEL_STAGE_ORDER, FunnelResult
from app.skills.metric_validation.schemas import (
    MIN_SIGNIFICANT_UPSTREAM,
    DataWarning,
    ValidationResult,
    WarningCode,
)


def validate_funnel(
    result: FunnelResult, *, min_significant_upstream: int = MIN_SIGNIFICANT_UPSTREAM
) -> ValidationResult:
    """
    Flag stages whose emptiness cannot be read as a growth signal.

    Deterministic and pure: no I/O, no clock, no randomness. The same funnel always
    produces the same verdict, so the guardrail is testable without an LLM in the
    loop — which is the point of it.
    """
    counts = result.counts
    warnings: list[DataWarning] = []
    terminal_stage = FUNNEL_STAGE_ORDER[-1]

    for upstream_stage, stage in pairwise(FUNNEL_STAGE_ORDER):
        upstream_count = getattr(counts, upstream_stage)
        stage_count = getattr(counts, stage)

        # An empty stage under an empty upstream is arithmetic, not a fault.
        if stage_count != 0 or upstream_count <= 0:
            continue

        if upstream_count < min_significant_upstream:
            code = WarningCode.COHORT_TOO_SMALL
            blocking = False
        elif stage == terminal_stage:
            code = WarningCode.TERMINAL_STAGE_EMPTY
            blocking = True
        else:
            code = WarningCode.IMPOSSIBLE_DROPOFF
            blocking = True

        warnings.append(
            DataWarning(
                code=code,
                stage=stage,
                upstream_stage=upstream_stage,
                blocking=blocking,
                message=code.message_template.format(
                    stage=stage,
                    upstream_stage=upstream_stage,
                    upstream_count=upstream_count,
                    threshold=min_significant_upstream,
                ),
                numbers={
                    "upstream_count": upstream_count,
                    "stage_count": stage_count,
                    "threshold": min_significant_upstream,
                },
            )
        )

    return ValidationResult(warnings=warnings)


__all__ = ["validate_funnel"]
