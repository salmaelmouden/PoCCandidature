"""Tests for anomaly_detection skill."""

from app.skills.anomaly_detection import detect_anomalies, detect_traffic_anomalies
from app.skills.anomaly_detection.schemas import AnomalyMethod


def test_z_score_detects_spike() -> None:
    series = [{"label": str(i), "value": 100.0} for i in range(10)]
    series.append({"label": "spike", "value": 400.0})
    result = detect_anomalies(series, method=AnomalyMethod.Z_SCORE, z_threshold=2.5)
    assert result.series_size == 11
    assert any(a.label == "spike" for a in result.anomalies)


def test_percent_change() -> None:
    series = [
        {"label": "d1", "value": 100.0},
        {"label": "d2", "value": 110.0},
        {"label": "d3", "value": 200.0},
    ]
    result = detect_anomalies(
        series, method=AnomalyMethod.PERCENT_CHANGE, percent_change_threshold=0.35
    )
    assert any(a.label == "d3" for a in result.anomalies)


def test_iqr_detects_outlier() -> None:
    series = [{"label": str(i), "value": float(i)} for i in range(1, 9)]
    series.append({"label": "out", "value": 100.0})
    result = detect_anomalies(series, method=AnomalyMethod.IQR)
    assert any(a.label == "out" for a in result.anomalies)


def test_rolling_mean() -> None:
    series = [{"label": str(i), "value": 50.0} for i in range(10)]
    series.append({"label": "jump", "value": 100.0})
    result = detect_anomalies(
        series,
        method=AnomalyMethod.ROLLING_MEAN,
        rolling_window=7,
        rolling_deviation_threshold=0.4,
    )
    assert any(a.label == "jump" for a in result.anomalies)


def test_empty_and_short_series() -> None:
    assert detect_anomalies([]).anomalies == []
    assert detect_anomalies([{"label": "a", "value": 1.0}]).anomalies == []


def test_traffic_helper_sets_kind() -> None:
    series = [{"label": str(i), "value": 10.0} for i in range(8)]
    series[7] = {"label": "7", "value": 50.0}
    result = detect_traffic_anomalies(series, method=AnomalyMethod.Z_SCORE, z_threshold=2.0)
    assert result.kind.value == "traffic"
