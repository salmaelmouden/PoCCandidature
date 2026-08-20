"""Deterministic weekly growth report generation."""

from __future__ import annotations

from app.skills.report_generation.schemas import ReportSection, WeeklyGrowthReport, WeeklyReportInput


def generate_weekly_report(payload: WeeklyReportInput | dict) -> WeeklyGrowthReport:
    """Build a structured + markdown weekly growth report from analytics inputs."""
    data = (
        payload if isinstance(payload, WeeklyReportInput) else WeeklyReportInput.model_validate(payload)
    )
    title = "Weekly Growth Report"
    if data.channel:
        title = f"Weekly Growth Report — {data.channel}"

    sections: list[ReportSection] = [
        _kpi_section(data),
        _funnel_section(data),
        _channel_section(data),
        _content_section(data),
        _actions_section(data),
    ]

    provenance = _provenance(data)
    markdown = _to_markdown(title, data, sections, provenance)
    return WeeklyGrowthReport(
        title=title,
        period_start=data.period_start,
        period_end=data.period_end,
        channel=data.channel,
        sections=sections,
        markdown=markdown,
        provenance_note=provenance,
    )


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1%}"


def _kpi_section(data: WeeklyReportInput) -> ReportSection:
    cur, prev, deltas = data.current_counts, data.previous_counts, data.relative_deltas
    bullets = [
        f"Views: {cur.get('views', 0):,} (prev {prev.get('views', 0):,}, Δ {_fmt_delta(deltas.get('views'))})",
        f"Signups: {cur.get('signups', 0):,} (prev {prev.get('signups', 0):,}, Δ {_fmt_delta(deltas.get('signups'))})",
        f"Premium: {cur.get('premium_users', 0):,} (prev {prev.get('premium_users', 0):,}, Δ {_fmt_delta(deltas.get('premium_users'))})",
    ]
    if data.anomaly_count:
        bullets.append(f"Traffic anomalies flagged: {data.anomaly_count}")
    return ReportSection(
        title="KPIs",
        body="Period-over-period funnel volume.",
        bullets=bullets,
    )


def _funnel_section(data: WeeklyReportInput) -> ReportSection:
    if data.bottleneck_from and data.bottleneck_to:
        rate = data.bottleneck_dropoff_rate
        rate_s = f"{rate:.1%}" if rate is not None else "n/a"
        body = f"Primary bottleneck: {data.bottleneck_from} → {data.bottleneck_to} (dropoff {rate_s})."
    else:
        body = "No clear bottleneck identified for this filter."
    return ReportSection(title="Funnel health", body=body, bullets=[])


def _channel_section(data: WeeklyReportInput) -> ReportSection:
    if not data.top_channels:
        return ReportSection(title="Channels", body="No channel breakdown available.", bullets=[])
    bullets = []
    for row in data.top_channels[:5]:
        bullets.append(
            f"{row.get('channel')}: signups={row.get('signups', 0)}, "
            f"premium_rate={float(row.get('premium_rate') or 0):.4f}"
        )
    return ReportSection(
        title="Channels",
        body="Top channels by signups in the current window.",
        bullets=bullets,
    )


def _content_section(data: WeeklyReportInput) -> ReportSection:
    if not data.content_gaps:
        return ReportSection(
            title="Content",
            body="No high-reach / low-conversion gaps flagged.",
            bullets=[],
        )
    bullets = []
    for gap in data.content_gaps[:5]:
        bullets.append(
            f"Topic “{gap.get('topic')}”: reach={gap.get('reach')}, "
            f"premium_rate={float(gap.get('premium_rate') or 0):.4f}"
        )
    return ReportSection(
        title="Content gaps",
        body="High reach with weak conversion.",
        bullets=bullets,
    )


def _actions_section(data: WeeklyReportInput) -> ReportSection:
    bullets = list(data.recommendations[:5])
    body = data.orchestrator_summary or "No orchestrator summary attached."
    if not bullets:
        bullets = ["Review bottleneck and weakest premium_rate channel next period."]
    return ReportSection(title="Suggested focus", body=body, bullets=bullets)


def _provenance(data: WeeklyReportInput) -> str:
    labels = ", ".join(data.dataset_labels) if data.dataset_labels else "unlabelled"
    syn = "includes synthetic_v1" if data.has_synthetic else "no synthetic flag"
    return f"Data provenance: labels=[{labels}]; {syn}. Not real company production data."


def _to_markdown(
    title: str,
    data: WeeklyReportInput,
    sections: list[ReportSection],
    provenance: str,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"**Period:** {data.period_start} → {data.period_end}"
        + (f" · **Channel:** {data.channel}" if data.channel else ""),
        "",
        f"_{provenance}_",
        "",
    ]
    for section in sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.body)
        lines.append("")
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        if section.bullets:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
