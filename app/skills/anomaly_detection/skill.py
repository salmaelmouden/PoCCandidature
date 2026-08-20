"""Deterministic anomaly detection (Python detects; AI interprets later)."""

from __future__ import annotations

import math
from statistics import mean, pstdev

from app.skills.anomaly_detection.schemas import (
    AnomalyDetectionResult,
    AnomalyKind,
    AnomalyMethod,
    AnomalyPoint,
    TimeSeriesPoint,
)


def detect_anomalies(
    series: list[TimeSeriesPoint] | list[dict],
    *,
    method: AnomalyMethod | str = AnomalyMethod.Z_SCORE,
    kind: AnomalyKind | str = AnomalyKind.GENERIC,
    z_threshold: float = 2.5,
    iqr_multiplier: float = 1.5,
    percent_change_threshold: float = 0.35,
    rolling_window: int = 7,
    rolling_deviation_threshold: float = 0.4,
) -> AnomalyDetectionResult:
    parsed = _parse_series(series)
    method_enum = AnomalyMethod(method)
    kind_enum = AnomalyKind(kind)

    if method_enum == AnomalyMethod.Z_SCORE:
        anomalies = _z_score(parsed, kind_enum, z_threshold)
    elif method_enum == AnomalyMethod.IQR:
        anomalies = _iqr(parsed, kind_enum, iqr_multiplier)
    elif method_enum == AnomalyMethod.PERCENT_CHANGE:
        anomalies = _percent_change(parsed, kind_enum, percent_change_threshold)
    elif method_enum == AnomalyMethod.ROLLING_MEAN:
        anomalies = _rolling_mean(
            parsed, kind_enum, rolling_window, rolling_deviation_threshold
        )
    else:
        raise ValueError(f"Unsupported method: {method_enum}")

    return AnomalyDetectionResult(
        kind=kind_enum,
        method=method_enum,
        anomalies=anomalies,
        series_size=len(parsed),
    )


def detect_traffic_anomalies(
    series: list[TimeSeriesPoint] | list[dict], **kwargs: float | int
) -> AnomalyDetectionResult:
    return detect_anomalies(series, kind=AnomalyKind.TRAFFIC, **kwargs)  # type: ignore[arg-type]


def detect_signup_anomalies(
    series: list[TimeSeriesPoint] | list[dict], **kwargs: float | int
) -> AnomalyDetectionResult:
    return detect_anomalies(series, kind=AnomalyKind.SIGNUP, **kwargs)  # type: ignore[arg-type]


def detect_conversion_anomalies(
    series: list[TimeSeriesPoint] | list[dict], **kwargs: float | int
) -> AnomalyDetectionResult:
    return detect_anomalies(series, kind=AnomalyKind.CONVERSION, **kwargs)  # type: ignore[arg-type]


def detect_channel_anomalies(
    series: list[TimeSeriesPoint] | list[dict], **kwargs: float | int
) -> AnomalyDetectionResult:
    return detect_anomalies(series, kind=AnomalyKind.CHANNEL, **kwargs)  # type: ignore[arg-type]


def detect_content_anomalies(
    series: list[TimeSeriesPoint] | list[dict], **kwargs: float | int
) -> AnomalyDetectionResult:
    return detect_anomalies(series, kind=AnomalyKind.CONTENT, **kwargs)  # type: ignore[arg-type]


def _parse_series(series: list[TimeSeriesPoint] | list[dict]) -> list[TimeSeriesPoint]:
    if not series:
        return []
    return [
        point if isinstance(point, TimeSeriesPoint) else TimeSeriesPoint.model_validate(point)
        for point in series
    ]


def _direction(value: float, baseline: float) -> str:
    return "up" if value >= baseline else "down"


def _z_score(
    series: list[TimeSeriesPoint], kind: AnomalyKind, threshold: float
) -> list[AnomalyPoint]:
    if len(series) < 3:
        return []
    values = [p.value for p in series]
    mu = mean(values)
    sigma = pstdev(values)
    if sigma == 0:
        return []
    anomalies: list[AnomalyPoint] = []
    for point in series:
        z = (point.value - mu) / sigma
        if abs(z) >= threshold:
            anomalies.append(
                AnomalyPoint(
                    label=point.label,
                    value=point.value,
                    method=AnomalyMethod.Z_SCORE,
                    kind=kind,
                    score=abs(z),
                    direction=_direction(point.value, mu),
                    details={"z_score": z, "mean": mu, "stdev": sigma},
                )
            )
    return anomalies


def _iqr(
    series: list[TimeSeriesPoint], kind: AnomalyKind, multiplier: float
) -> list[AnomalyPoint]:
    if len(series) < 4:
        return []
    values = sorted(p.value for p in series)
    q1 = _percentile(values, 25)
    q3 = _percentile(values, 75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    mid = (q1 + q3) / 2
    anomalies: list[AnomalyPoint] = []
    for point in series:
        if point.value < lower or point.value > upper:
            distance = lower - point.value if point.value < lower else point.value - upper
            anomalies.append(
                AnomalyPoint(
                    label=point.label,
                    value=point.value,
                    method=AnomalyMethod.IQR,
                    kind=kind,
                    score=distance if iqr == 0 else distance / iqr,
                    direction=_direction(point.value, mid),
                    details={"q1": q1, "q3": q3, "iqr": iqr, "lower": lower, "upper": upper},
                )
            )
    return anomalies


def _percent_change(
    series: list[TimeSeriesPoint], kind: AnomalyKind, threshold: float
) -> list[AnomalyPoint]:
    anomalies: list[AnomalyPoint] = []
    for prev, curr in zip(series, series[1:], strict=False):
        if prev.value == 0:
            if curr.value != 0:
                change = math.inf
            else:
                continue
        else:
            change = (curr.value - prev.value) / abs(prev.value)
        if abs(change) >= threshold:
            anomalies.append(
                AnomalyPoint(
                    label=curr.label,
                    value=curr.value,
                    method=AnomalyMethod.PERCENT_CHANGE,
                    kind=kind,
                    score=abs(change) if math.isfinite(change) else 999.0,
                    direction=_direction(curr.value, prev.value),
                    details={
                        "percent_change": change if math.isfinite(change) else 999.0,
                        "previous_value": prev.value,
                        "previous_label": prev.label,
                    },
                )
            )
    return anomalies


def _rolling_mean(
    series: list[TimeSeriesPoint],
    kind: AnomalyKind,
    window: int,
    threshold: float,
) -> list[AnomalyPoint]:
    if window < 2 or len(series) <= window:
        return []
    anomalies: list[AnomalyPoint] = []
    for idx in range(window, len(series)):
        window_vals = [series[j].value for j in range(idx - window, idx)]
        baseline = mean(window_vals)
        point = series[idx]
        if baseline == 0:
            if point.value == 0:
                continue
            deviation = math.inf
        else:
            deviation = (point.value - baseline) / abs(baseline)
        if abs(deviation) >= threshold:
            anomalies.append(
                AnomalyPoint(
                    label=point.label,
                    value=point.value,
                    method=AnomalyMethod.ROLLING_MEAN,
                    kind=kind,
                    score=abs(deviation) if math.isfinite(deviation) else 999.0,
                    direction=_direction(point.value, baseline),
                    details={
                        "rolling_mean": baseline,
                        "window": window,
                        "deviation": deviation if math.isfinite(deviation) else 999.0,
                    },
                )
            )
    return anomalies


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight
