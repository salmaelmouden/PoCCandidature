"""Weekly report application service — dashboard + optional orchestrator + skill."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.growth_orchestrator_agent import GrowthOrchestratorAgent, OrchestratorQuestion
from app.observability import flush_tracing, observation
from app.services.dashboard import (
    get_acquisition,
    get_content,
    get_overview,
)
from app.skills.report_generation import WeeklyGrowthReport, generate_weekly_report


def build_weekly_report(
    session: Session,
    *,
    days: int = 7,
    channel: str | None = None,
    as_of: date | None = None,
    include_orchestrator: bool = True,
    question: str = "What should we do about Premium conversion this week?",
) -> WeeklyGrowthReport:
    """Assemble analytics (+ optional orchestrator) into a weekly report."""
    with observation(
        "build_weekly_report",
        input={"question": question, "days": days, "channel": channel},
        tags=["report"],
    ) as span:
        overview = get_overview(session, days=days, channel=channel, as_of=as_of)
        acquisition = get_acquisition(session, days=days, as_of=as_of)
        content = get_content(session, days=days, channel=channel, as_of=as_of)

        orchestrator_summary = None
        recommendations: list[str] = []
        if include_orchestrator:
            orch = GrowthOrchestratorAgent().run(
                session,
                OrchestratorQuestion(
                    question=question,
                    days=days,
                    channel=channel,
                    as_of=as_of,
                ),
            )
            orchestrator_summary = orch.summary
            if orch.strategy_report:
                recommendations = [
                    f"[{r.priority.value}] {r.title}: {r.action}"
                    for r in orch.strategy_report.recommendations
                ]

        top_channels = [
            {
                "channel": row.channel,
                "signups": row.signups,
                "premium_rate": row.premium_rate,
            }
            for row in sorted(acquisition.rows, key=lambda r: (-r.signups, -r.views))[:5]
        ]
        gaps = [
            {
                "topic": g.topic,
                "reach": g.reach,
                "premium_rate": g.premium_rate,
            }
            for g in content.reach_conversion_gaps[:5]
        ]

        report = generate_weekly_report(
            {
                "period_start": overview.period.start,
                "period_end": overview.period.end,
                "channel": channel,
                "current_counts": overview.current_counts,
                "previous_counts": overview.previous_counts,
                "relative_deltas": overview.relative_deltas,
                "bottleneck_from": overview.funnel.bottleneck_from_stage,
                "bottleneck_to": overview.funnel.bottleneck_to_stage,
                "bottleneck_dropoff_rate": overview.funnel.bottleneck_dropoff_rate,
                "anomaly_count": len(overview.traffic_anomalies.anomalies),
                "top_channels": top_channels,
                "content_gaps": gaps,
                "orchestrator_summary": orchestrator_summary,
                "recommendations": recommendations,
                "dataset_labels": sorted(overview.dataset_labels),
                "has_synthetic": overview.has_synthetic,
            }
        )
        span.update(output={"title": report.title, "sections": len(report.sections)})
        flush_tracing()
        return report


def write_report_markdown(report: WeeklyGrowthReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.markdown, encoding="utf-8")
    return path
