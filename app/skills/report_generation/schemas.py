"""Pydantic contracts for report_generation."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    body: str
    bullets: list[str] = Field(default_factory=list)


class WeeklyReportInput(BaseModel):
    period_start: date
    period_end: date
    channel: str | None = None
    current_counts: dict[str, int]
    previous_counts: dict[str, int]
    relative_deltas: dict[str, float | None] = Field(default_factory=dict)
    bottleneck_from: str | None = None
    bottleneck_to: str | None = None
    bottleneck_dropoff_rate: float | None = None
    anomaly_count: int = 0
    top_channels: list[dict] = Field(default_factory=list)
    content_gaps: list[dict] = Field(default_factory=list)
    orchestrator_summary: str | None = None
    recommendations: list[str] = Field(default_factory=list)
    dataset_labels: list[str] = Field(default_factory=list)
    has_synthetic: bool = False


class WeeklyGrowthReport(BaseModel):
    title: str
    period_start: date
    period_end: date
    channel: str | None
    sections: list[ReportSection]
    markdown: str
    provenance_note: str
