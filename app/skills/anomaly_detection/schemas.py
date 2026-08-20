"""Schemas for anomaly_detection skill."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AnomalyMethod(StrEnum):
    Z_SCORE = "z_score"
    IQR = "iqr"
    PERCENT_CHANGE = "percent_change"
    ROLLING_MEAN = "rolling_mean"


class AnomalyKind(StrEnum):
    TRAFFIC = "traffic"
    SIGNUP = "signup"
    CONVERSION = "conversion"
    CHANNEL = "channel"
    CONTENT = "content"
    GENERIC = "generic"


class TimeSeriesPoint(BaseModel):
    label: str = Field(description="Date or period label")
    value: float


class AnomalyPoint(BaseModel):
    label: str
    value: float
    method: AnomalyMethod
    kind: AnomalyKind
    score: float = Field(description="Method-specific severity score")
    direction: str = Field(description="up | down")
    details: dict[str, float | str | int]


class AnomalyDetectionResult(BaseModel):
    kind: AnomalyKind
    method: AnomalyMethod
    anomalies: list[AnomalyPoint]
    series_size: int
