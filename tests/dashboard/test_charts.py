"""Tests for the Altair builders.

`to_dict()` runs Altair's own schema validation, so building a spec is a real
assertion: it catches an encoding channel that does not exist, a mark property
passed where a channel was expected, and a scale that cannot resolve. The rest
of these tests cover the two things validation cannot see — that the numbers put
on screen are the right ones, and that an empty period renders instead of
raising.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from dashboard import charts
from dashboard.theme import DARK_TOKENS, LIGHT_TOKENS

BOTH_THEMES = pytest.mark.parametrize(
    "tokens", [LIGHT_TOKENS, DARK_TOKENS], ids=["light", "dark"]
)


@dataclass(frozen=True)
class ChannelRow:
    channel: str
    views: int = 0
    visits: int = 0
    signups: int = 0
    activated_users: int = 0
    premium_users: int = 0
    visit_rate: float = 0.0
    signup_rate: float = 0.0
    premium_rate: float = 0.0


@dataclass(frozen=True)
class Conversion:
    from_stage: str
    to_stage: str
    rate: float


@dataclass(frozen=True)
class Anomaly:
    label: str
    value: float
    direction: str
    score: float = 3.0
    method: str = "z_score"


@dataclass(frozen=True)
class Content:
    content_id: str
    title: str
    topic: str
    reach: int
    signups: int
    premium_users: int
    premium_rate: float


@dataclass(frozen=True)
class Topic:
    topic: str
    content_count: int
    total_reach: int
    avg_content_value_score: float


START = date(2026, 5, 1)
SERIES = [(START + timedelta(days=index), 1000 + index * 37) for index in range(30)]
COUNTS = {
    "views": 120_000,
    "visits": 41_000,
    "signups": 3_100,
    "activated_users": 2_400,
    "premium_users": 410,
}
CONVERSIONS = [
    Conversion("views", "visits", 0.3417),
    Conversion("visits", "signups", 0.0756),
    Conversion("signups", "activated_users", 0.7742),
    Conversion("activated_users", "premium_users", 0.1708),
]
CHANNELS = [
    ChannelRow("YouTube", 60_000, 21_000, 1_700, 1_300, 220, 0.35, 0.081, 0.169),
    ChannelRow("Organic Search", 30_000, 11_000, 800, 600, 110, 0.36, 0.072, 0.183),
    ChannelRow("Paid", 20_000, 6_000, 400, 300, 50, 0.30, 0.066, 0.166),
]
CONTENTS = [
    Content(f"c{i}", f"Contenu {i}", "ETFs", 5_000 + i * 900, 120 + i, 20 + i, 0.02 + i / 500)
    for i in range(9)
]
TOPICS = [Topic("ETFs", 12, 90_000, 0.61), Topic("Crypto", 7, 40_000, 0.42)]


def _spec(chart) -> dict:
    return chart.to_dict()


def _rows(spec: dict, field: str) -> list[dict]:
    """Inline dataset carrying `field`.

    A layered chart inlines one dataset per layer — the zero rule, the reference
    line — so picking "the first one" reads whichever happened to be emitted
    first rather than the one under test.
    """
    for values in spec["datasets"].values():
        if values and field in values[0]:
            return values
    raise AssertionError(f"no inline dataset carries {field!r}")


# ------------------------------------------------------------------- validity


@BOTH_THEMES
def test_every_builder_produces_a_valid_spec(tokens) -> None:
    built = [
        charts.trend_chart(SERIES, [], tokens, title="Vues"),
        charts.funnel_chart(COUNTS, CONVERSIONS, tokens),
        charts.conversion_delta_chart({"views_to_visits": 0.012}, tokens),
        charts.channel_volume_chart(CHANNELS, tokens),
        charts.channel_rate_chart(CHANNELS, tokens),
        charts.content_scatter(CONTENTS, tokens, gap_ids=["c3"]),
        charts.topic_chart(TOPICS, tokens),
    ]

    assert all(_spec(chart) for chart in built)


@BOTH_THEMES
def test_empty_inputs_render_instead_of_raising(tokens) -> None:
    """A filter can legitimately select a period with no rows in it."""
    built = [
        charts.trend_chart([], [], tokens, title="Vues"),
        charts.conversion_delta_chart({}, tokens),
        charts.channel_volume_chart([], tokens),
        charts.channel_rate_chart([], tokens),
        charts.content_scatter([], tokens),
        charts.topic_chart([], tokens),
    ]

    assert all(_spec(chart) for chart in built)


def test_dark_specs_use_the_dark_steps() -> None:
    light = json.dumps(_spec(charts.channel_volume_chart(CHANNELS, LIGHT_TOKENS)))
    dark = json.dumps(_spec(charts.channel_volume_chart(CHANNELS, DARK_TOKENS)))

    assert LIGHT_TOKENS.series in light
    assert DARK_TOKENS.series in dark
    assert light != dark


# --------------------------------------------------------------------- funnel


def test_funnel_plots_share_of_the_top_stage() -> None:
    """Raw counts on a linear axis turn every stage after the first into a line."""
    spec = _spec(charts.funnel_chart(COUNTS, CONVERSIONS, LIGHT_TOKENS))
    values = _rows(spec, "etape")

    by_stage = {row["etape"]: row for row in values}
    assert by_stage["Vues"]["part"] == pytest.approx(100.0)
    assert by_stage["Visites"]["part"] == pytest.approx(100 * 41_000 / 120_000)
    assert by_stage["Premium"]["part"] == pytest.approx(100 * 410 / 120_000)


def test_funnel_keeps_absolute_counts_for_the_labels() -> None:
    spec = _spec(charts.funnel_chart(COUNTS, CONVERSIONS, LIGHT_TOKENS))
    values = _rows(spec, "etape")

    assert {row["valeur"] for row in values} == set(COUNTS.values())


def test_funnel_carries_the_incoming_conversion_rate() -> None:
    spec = _spec(charts.funnel_chart(COUNTS, CONVERSIONS, LIGHT_TOKENS))
    values = _rows(spec, "etape")
    by_stage = {row["etape"]: row for row in values}

    assert by_stage["Vues"]["passage"] == "—"  # nothing converts into the top
    assert by_stage["Visites"]["passage"] == "34,2 %"


def test_funnel_uses_the_ordinal_ramp_not_categorical_hues() -> None:
    """Stages are ordered, so they take one hue in steps — not eight identities."""
    spec = json.dumps(_spec(charts.funnel_chart(COUNTS, CONVERSIONS, LIGHT_TOKENS)))

    for step in LIGHT_TOKENS.funnel_ramp:
        assert step in spec
    assert LIGHT_TOKENS.categorical[1] not in spec  # no orange anywhere


def test_funnel_survives_a_period_with_no_traffic() -> None:
    empty = dict.fromkeys(COUNTS, 0)

    assert _spec(charts.funnel_chart(empty, [], LIGHT_TOKENS))


# ---------------------------------------------------------------------- delta


def test_delta_drops_transitions_with_no_comparison_base() -> None:
    """`None` means "no previous period", which is not the same as "no change"."""
    spec = _spec(
        charts.conversion_delta_chart(
            {"views_to_visits": 0.012, "visits_to_signups": None}, LIGHT_TOKENS
        )
    )
    values = _rows(spec, "transition")

    assert [row["transition"] for row in values] == ["Vues → Visites"]


def test_delta_converts_ratios_to_percentage_points() -> None:
    spec = _spec(charts.conversion_delta_chart({"views_to_visits": 0.0123}, LIGHT_TOKENS))
    values = _rows(spec, "points")

    assert values[0]["points"] == pytest.approx(1.23)
    assert values[0]["sens"] == "hausse"


def test_delta_scale_is_symmetric_around_zero() -> None:
    """An asymmetric diverging axis makes one direction look larger than it is."""
    spec = _spec(
        charts.conversion_delta_chart(
            {"a_to_b": 0.05, "c_to_d": -0.01}, LIGHT_TOKENS
        )
    )
    domain = spec["layer"][1]["encoding"]["x"]["scale"]["domain"]

    assert domain[0] == pytest.approx(-domain[1])


# ------------------------------------------------------------------- channels


def test_channel_volume_sorts_descending() -> None:
    spec = _spec(charts.channel_volume_chart(CHANNELS, LIGHT_TOKENS, metric="signups"))
    values = _rows(spec, "valeur")

    assert [row["valeur"] for row in values] == [1_700, 800, 400]


def test_channel_volume_uses_one_colour_for_every_bar() -> None:
    """Darker-where-bigger on nominal categories re-encodes the bar's own length."""
    spec = _spec(charts.channel_volume_chart(CHANNELS, LIGHT_TOKENS))

    bars = spec["layer"][0]
    assert bars["mark"]["color"] == LIGHT_TOKENS.series
    assert "color" not in bars["encoding"]


def test_channel_volume_switches_measure() -> None:
    spec = _spec(charts.channel_volume_chart(CHANNELS, LIGHT_TOKENS, metric="premium_users"))
    values = _rows(spec, "valeur")

    assert [row["valeur"] for row in values] == [220, 110, 50]


def test_channel_names_are_translated() -> None:
    spec = _spec(charts.channel_volume_chart(CHANNELS, LIGHT_TOKENS))
    values = _rows(spec, "canal")

    assert "Recherche organique" in {row["canal"] for row in values}


def test_channel_rates_share_one_axis_with_three_series() -> None:
    """Three rates, one unit, one scale — the alternative would be a dual axis."""
    spec = _spec(charts.channel_rate_chart(CHANNELS, LIGHT_TOKENS))
    values = _rows(spec, "canal")

    assert len(values) == len(CHANNELS) * len(charts.RATE_FIELDS)
    assert spec["encoding"]["color"]["scale"]["range"] == list(LIGHT_TOKENS.categorical[:3])
    youtube_visit = next(
        row for row in values if row["canal"] == "YouTube" and row["passage"] == "Vues → Visites"
    )
    assert youtube_visit["taux"] == pytest.approx(35.0)


def test_channel_rates_keep_a_legend() -> None:
    """Two or more series always get one — identity is never colour alone."""
    spec = _spec(charts.channel_rate_chart(CHANNELS, LIGHT_TOKENS))

    assert spec["encoding"]["color"]["legend"]["orient"] == "top"


# -------------------------------------------------------------------- content


def test_scatter_flags_only_the_reported_gaps() -> None:
    spec = _spec(charts.content_scatter(CONTENTS, LIGHT_TOKENS, gap_ids=["c3", "c7"]))
    values = _rows(spec, "contenu")

    flagged = {row["contenu"] for row in values if row["etat"].startswith("Portée élevée")}
    assert flagged == {"Contenu 3", "Contenu 7"}


def test_scatter_greys_out_everything_that_is_not_the_story() -> None:
    """Emphasis, not categorical: the rest of the catalogue is context."""
    spec = _spec(charts.content_scatter(CONTENTS, LIGHT_TOKENS, gap_ids=["c3"]))
    palette = spec["layer"][0]["encoding"]["color"]["scale"]["range"]

    assert palette == [LIGHT_TOKENS.serious, LIGHT_TOKENS.series_muted]


def test_scatter_converts_the_rate_to_a_percentage() -> None:
    spec = _spec(charts.content_scatter(CONTENTS[:1], LIGHT_TOKENS))
    values = _rows(spec, "premium")

    assert values[0]["premium"] == pytest.approx(2.0)


def test_topic_chart_sorts_by_score() -> None:
    spec = _spec(charts.topic_chart(TOPICS, LIGHT_TOKENS))
    values = _rows(spec, "score")

    assert [row["score"] for row in values] == [0.61, 0.42]


# ---------------------------------------------------------------------- trend


def test_trend_marks_only_the_flagged_days() -> None:
    flagged = str(START + timedelta(days=7))
    spec = _spec(
        charts.trend_chart(
            SERIES, [Anomaly(label=flagged, value=1259.0, direction="up")], LIGHT_TOKENS,
            title="Vues",
        )
    )

    # Anomaly layers are only added when there is something to mark.
    assert len(spec["layer"]) == 7


def test_trend_without_anomalies_skips_those_layers() -> None:
    spec = _spec(charts.trend_chart(SERIES, [], LIGHT_TOKENS, title="Vues"))

    assert len(spec["layer"]) == 5


def test_trend_ships_a_hover_layer() -> None:
    """An HTML chart is interactive; a value should not need the table to be read."""
    spec = json.dumps(
        _spec(charts.trend_chart(SERIES, [], LIGHT_TOKENS, title="Vues")), default=str
    )

    assert "mouseover" in spec
    assert "tooltip" in spec


def test_anomaly_table_is_the_readable_twin() -> None:
    frame = charts.anomaly_table(
        [Anomaly(label="2026-05-08", value=1259.0, direction="up", score=3.14)]
    )

    assert list(frame.columns) == ["Jour", "Valeur", "Sens", "Méthode", "Score"]
    assert frame.loc[0, "Sens"] == "hausse"
    assert frame.loc[0, "Score"] == 3.14


def test_anomaly_table_is_empty_when_nothing_was_flagged() -> None:
    assert charts.anomaly_table([]).empty
