"""Typed tools for growth_experiment_analyst_agent."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.schemas import AnalystReport
from app.db.repositories import ExperimentRepository
from app.skills.experiment_analysis import compare_variants


def tool_list_experiments(session: Session, *, status: str | None = None) -> dict[str, Any]:
    repo = ExperimentRepository(session)
    rows = repo.list_experiments(status=status)
    return {
        "experiments": [
            {
                "experiment_key": e.experiment_key,
                "name": e.name,
                "status": e.status,
                "primary_metric": e.primary_metric,
                "hypothesis": e.hypothesis,
                "is_synthetic": e.is_synthetic,
                "dataset_label": e.dataset_label,
            }
            for e in rows
        ],
        "count": len(rows),
    }


def tool_analyze_experiment(
    session: Session,
    *,
    experiment_key: str,
    alpha: float = 0.05,
) -> dict[str, Any]:
    repo = ExperimentRepository(session)
    exp = repo.get_by_key(experiment_key)
    if exp is None:
        return {"ok": False, "error": f"Unknown experiment_key={experiment_key!r}"}

    results = repo.list_results(exp.id)
    by_variant = {r.variant: r for r in results}
    if "control" not in by_variant or "treatment" not in by_variant:
        return {
            "ok": False,
            "error": "Need both control and treatment variants to compare.",
            "variants": list(by_variant),
        }

    control = by_variant["control"]
    treatment = by_variant["treatment"]
    comparison = compare_variants(
        {
            "variant": control.variant,
            "users": control.users,
            "conversions": control.conversions,
        },
        {
            "variant": treatment.variant,
            "users": treatment.users,
            "conversions": treatment.conversions,
        },
        alpha=alpha,
    )
    return {
        "ok": True,
        "experiment_key": exp.experiment_key,
        "name": exp.name,
        "hypothesis": exp.hypothesis,
        "status": exp.status,
        "primary_metric": exp.primary_metric,
        "is_synthetic": exp.is_synthetic,
        "dataset_label": exp.dataset_label,
        "comparison": comparison.model_dump(),
    }


def tool_get_analyst_report(
    session: Session,
    *,
    question: str,
    days: int = 30,
    channel: str | None = None,
    as_of: date | None = None,
) -> AnalystReport:
    return GrowthDataAnalystAgent().run(
        session,
        AnalystQuestion(question=question, days=days, channel=channel, as_of=as_of),
    )
