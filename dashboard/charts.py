"""Altair chart builders for the synthetic-funnel pages — pure, no Streamlit runtime.

Every builder takes a resolved :class:`~dashboard.theme.Tokens` so the same
chart renders correctly in either mode: the dark variants are stepped for the
dark surface rather than being an automatic inversion of the light ones.

Form choices worth stating once, because they are the part that is easy to get
wrong later:

* the funnel is an **ordinal** ramp (one hue, stages are ordered), never eight
  categorical colours — the stages are not competing identities;
* stage-to-stage change is a **diverging** bar around zero, because the reader's
  question there is a sign, not a magnitude;
* channel rates share one axis and one unit, so they are a grouped bar rather
  than two scales pretending to correlate;
* wherever a colour sits below 3:1 on its surface, the chart carries direct
  labels and the page carries a table twin — no value is reachable by hue alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import altair as alt
import pandas as pd

from dashboard.formatting import (
    channel_label,
    fmt_int,
    stage_short,
    topic_label,
    transition_label,
)
from dashboard.theme import Tokens

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"

#: Rate keys carried through the grouped channel chart, in funnel order.
RATE_FIELDS: tuple[tuple[str, str], ...] = (
    ("visit_rate", "Vues → Visites"),
    ("signup_rate", "Visites → Inscriptions"),
    ("premium_rate", "Activés → Premium"),
)


def _title(text: str, tokens: Tokens) -> alt.TitleParams:
    return alt.TitleParams(
        text,
        anchor="start",
        font=FONT,
        fontSize=13,
        fontWeight=600,
        color=tokens.ink_soft,
        offset=12,
    )


def finalize(chart, tokens: Tokens, *, title: str, height: int):
    """Shared chrome: recessive hairline axes, no view border, brand typeface."""
    return (
        chart.properties(height=height, title=_title(title, tokens))
        .configure_view(strokeWidth=0, fill=None)
        .configure_axis(
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight=500,
            labelColor=tokens.ink_muted,
            titleColor=tokens.ink_muted,
            gridColor=tokens.grid,
            gridWidth=1,
            domainColor=tokens.axis,
            tickColor=tokens.axis,
            labelPadding=6,
        )
        .configure_legend(
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            labelColor=tokens.ink_soft,
            titleColor=tokens.ink_muted,
            symbolType="circle",
            symbolSize=90,
            offset=8,
        )
        .configure(background="transparent")
    )


# --------------------------------------------------------------------- trend


def trend_chart(
    series: Sequence[tuple[date, int]],
    anomalies: Sequence[object],
    tokens: Tokens,
    *,
    title: str,
    y_title: str = "Vues par jour",
) -> alt.LayerChart:
    """Daily series with flagged points called out.

    One series, so no legend: the title names what is plotted. Anomalies wear a
    status colour and a label, never colour alone — the reader who cannot tell
    the dot from the line still gets the date on the axis and the row in the
    table underneath.
    """
    # The detector labels its points with `date.isoformat()`, so matching happens
    # on that string, before the column becomes timestamps — comparing a
    # `Timestamp` against "2026-05-08" silently matches nothing.
    flagged = {
        getattr(point, "label", None): getattr(point, "direction", "")
        for point in anomalies
    }
    rows = [{"jour": day, "valeur": int(value)} for day, value in series]
    marked = [
        {**row, "sens": "hausse" if flagged[row["jour"].isoformat()] == "up" else "baisse"}
        for row in rows
        if row["jour"].isoformat() in flagged
    ]

    def _framed(records: list[dict], extra: tuple[str, ...] = ()) -> pd.DataFrame:
        if not records:
            columns = {"jour": pd.Series(dtype="datetime64[ns]"), "valeur": []}
            columns.update({name: [] for name in extra})
            return pd.DataFrame(columns)
        built = pd.DataFrame(records)
        # A column of `datetime.date` lands as object dtype, and a temporal
        # encoding over object dtype is a coin toss. Make it explicit.
        built["jour"] = pd.to_datetime(built["jour"])
        return built

    frame = _framed(rows)
    marks = _framed(marked, extra=("sens",))

    x = alt.X("jour:T", title=None, axis=alt.Axis(format="%d %b", tickCount=6))
    y = alt.Y("valeur:Q", title=y_title, scale=alt.Scale(zero=False, nice=True))
    tooltip = [
        alt.Tooltip("jour:T", title="Jour", format="%d %B %Y"),
        alt.Tooltip("valeur:Q", title=y_title, format=",.0f"),
    ]

    area = (
        alt.Chart(frame)
        .mark_area(
            line=False,
            opacity=0.10,
            color=tokens.series,
        )
        .encode(x=x, y=y)
    )
    line = (
        alt.Chart(frame)
        .mark_line(strokeWidth=2, color=tokens.series, strokeJoin="round", strokeCap="round")
        .encode(x=x, y=y)
    )

    hover = alt.selection_point(nearest=True, on="mouseover", fields=["jour"], empty=False)
    hit = (
        alt.Chart(frame)
        .mark_rule(opacity=0, strokeWidth=14)
        .encode(x=x, tooltip=tooltip)
        .add_params(hover)
    )
    crosshair = (
        alt.Chart(frame)
        .mark_rule(color=tokens.axis, strokeWidth=1)
        .encode(x=x)
        .transform_filter(hover)
    )
    focus = (
        alt.Chart(frame)
        .mark_point(
            filled=True,
            size=90,
            color=tokens.series,
            stroke=tokens.surface,
            strokeWidth=2,
        )
        .encode(x=x, y=y)
        .transform_filter(hover)
    )

    layers = [area, line, crosshair, hit, focus]

    if not marks.empty:
        alerts = (
            alt.Chart(marks)
            .mark_point(
                filled=True,
                size=130,
                color=tokens.critical,
                stroke=tokens.surface,
                strokeWidth=2,
            )
            .encode(
                x=x,
                y=y,
                tooltip=[
                    alt.Tooltip("jour:T", title="Jour", format="%d %B %Y"),
                    alt.Tooltip("valeur:Q", title=y_title, format=",.0f"),
                    alt.Tooltip("sens:N", title="Anomalie"),
                ],
            )
        )
        alert_labels = (
            alt.Chart(marks)
            .mark_text(dy=-16, fontSize=10, font=FONT, fontWeight=600, color=tokens.ink_soft)
            .encode(x=x, y=y, text=alt.Text("valeur:Q", format=",.0f"))
        )
        layers.extend([alerts, alert_labels])

    return finalize(alt.layer(*layers), tokens, title=title, height=260)


# -------------------------------------------------------------------- funnel


def funnel_chart(
    counts: dict[str, int],
    conversions: Sequence[object],
    tokens: Tokens,
    *,
    title: str = "Entonnoir — part du sommet conservée",
) -> alt.LayerChart:
    """Stages as a share of the top of funnel, labelled with absolute counts.

    Plotted as a share rather than raw counts because a funnel spans orders of
    magnitude: on a linear count axis every stage after the first is a hairline.
    The absolute number stays on the bar, so nothing is lost.
    """
    stages = list(counts.keys())
    top = max(counts.get(stages[0], 0), 1) if stages else 1
    rate_by_stage = {
        getattr(conversion, "to_stage", ""): getattr(conversion, "rate", None)
        for conversion in conversions
    }

    frame = pd.DataFrame(
        [
            {
                "etape": stage_short(stage),
                "rang": index,
                "valeur": int(value),
                "part": 100.0 * int(value) / top,
                "passage": (
                    f"{100 * rate_by_stage[stage]:.1f} %".replace(".", ",")
                    if rate_by_stage.get(stage) is not None
                    else "—"
                ),
            }
            for index, (stage, value) in enumerate(counts.items())
        ]
    )
    order = frame["etape"].tolist()

    y = alt.Y("etape:N", sort=order, title=None)
    bars = (
        alt.Chart(frame)
        .mark_bar(height=22, cornerRadiusEnd=4)
        .encode(
            y=y,
            x=alt.X("part:Q", title="Part des vues (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(
                "etape:N",
                sort=order,
                scale=alt.Scale(domain=order, range=list(tokens.funnel_ramp[: len(order)])),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("etape:N", title="Étape"),
                alt.Tooltip("valeur:Q", title="Volume", format=",.0f"),
                alt.Tooltip("part:Q", title="Part des vues %", format=".2f"),
                alt.Tooltip("passage:N", title="Conversion depuis l'étape précédente"),
            ],
        )
    )
    labels = (
        alt.Chart(frame)
        .transform_calculate(
            etiquette="format(datum.valeur, ',') + '   ·   ' + datum.passage",
        )
        .mark_text(align="left", dx=8, fontSize=11, font=FONT, color=tokens.ink_soft)
        .encode(y=y, x=alt.X("part:Q"), text=alt.Text("etiquette:N"))
    )
    return finalize(bars + labels, tokens, title=title, height=max(210, 46 * len(order)))


def conversion_delta_chart(
    deltas: dict[str, float | None],
    tokens: Tokens,
    *,
    title: str = "Variation des taux de passage — période vs précédente",
) -> alt.LayerChart:
    """Signed change per transition, in percentage points.

    Diverging by design: the reader's first question is which way it moved, so
    the two arms take the warm/cool pair and zero keeps a neutral rule.
    """
    rows = [
        {
            "transition": transition_label(key),
            "points": round(100 * value, 2),
            "sens": "hausse" if value >= 0 else "baisse",
        }
        for key, value in deltas.items()
        if value is not None
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame({"transition": [], "points": [], "sens": []})

    order = frame["transition"].tolist()
    y = alt.Y("transition:N", sort=order, title=None)
    span = max(1.0, float(frame["points"].abs().max()) if not frame.empty else 1.0) * 1.35

    bars = (
        alt.Chart(frame)
        .mark_bar(height=20, cornerRadiusEnd=4)
        .encode(
            y=y,
            x=alt.X(
                "points:Q",
                title="Points de pourcentage",
                scale=alt.Scale(domain=[-span, span]),
            ),
            color=alt.Color(
                "sens:N",
                scale=alt.Scale(
                    domain=["hausse", "baisse"],
                    range=[tokens.categorical[0], tokens.categorical[7]],
                ),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("transition:N", title="Passage"),
                alt.Tooltip("points:Q", title="Variation (pt)", format="+.2f"),
            ],
        )
    )
    zero = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color=tokens.axis, strokeWidth=1)
        .encode(x="x:Q")
    )
    # Align and dx are mark properties, not encoding channels, so the two sides
    # are drawn as two layers rather than one conditional encoding.
    label_text = alt.Text("etiquette:N")
    labelled = alt.Chart(frame).transform_calculate(
        etiquette="(datum.points >= 0 ? '+' : '−') + format(abs(datum.points), '.2f') + ' pt'"
    )
    up_labels = (
        labelled.transform_filter(alt.datum.points >= 0)
        .mark_text(align="left", dx=8, fontSize=11, font=FONT, color=tokens.ink_soft)
        .encode(y=y, x=alt.X("points:Q"), text=label_text)
    )
    down_labels = (
        labelled.transform_filter(alt.datum.points < 0)
        .mark_text(align="right", dx=-8, fontSize=11, font=FONT, color=tokens.ink_soft)
        .encode(y=y, x=alt.X("points:Q"), text=label_text)
    )
    return finalize(
        zero + bars + up_labels + down_labels,
        tokens,
        title=title,
        height=max(190, 46 * len(order)),
    )


# ------------------------------------------------------------------ channels


def channel_volume_chart(
    rows: Sequence[object],
    tokens: Tokens,
    *,
    metric: str = "signups",
    title: str = "Inscriptions par canal",
) -> alt.LayerChart:
    """One measure across channels: one series, one colour, value at the tip.

    Deliberately *not* darker-where-bigger — channels have no natural order, and
    a value ramp there would spend the only free channel restating bar length.
    """
    frame = pd.DataFrame(
        [
            {
                "canal": channel_label(getattr(row, "channel", "")),
                "valeur": int(getattr(row, metric, 0) or 0),
            }
            for row in rows
        ]
    )
    if frame.empty:
        frame = pd.DataFrame({"canal": [], "valeur": []})
    frame = frame.sort_values("valeur", ascending=False).reset_index(drop=True)
    order = frame["canal"].tolist()

    y = alt.Y("canal:N", sort=order, title=None)
    bars = (
        alt.Chart(frame)
        .mark_bar(height=20, cornerRadiusEnd=4, color=tokens.series)
        .encode(
            y=y,
            x=alt.X("valeur:Q", title=None, axis=alt.Axis(format="~s")),
            tooltip=[
                alt.Tooltip("canal:N", title="Canal"),
                alt.Tooltip("valeur:Q", title="Volume", format=",.0f"),
            ],
        )
    )
    labels = (
        alt.Chart(frame)
        .mark_text(align="left", dx=8, fontSize=11, font=FONT, color=tokens.ink_soft)
        .encode(y=y, x=alt.X("valeur:Q"), text=alt.Text("valeur:Q", format=",.0f"))
    )
    return finalize(bars + labels, tokens, title=title, height=max(200, 42 * len(order)))


def channel_rate_chart(
    rows: Sequence[object],
    tokens: Tokens,
    *,
    title: str = "Taux de passage par canal",
) -> alt.Chart:
    """Three rates per channel on one shared axis.

    They are all conversion rates in the same unit, so they belong on the same
    scale — grouping them is what lets a reader see that a channel is strong at
    the top and weak at the bottom. Three series only: the first three
    categorical slots are the ones that clear the all-pairs colour-vision gates.
    """
    records = []
    for row in rows:
        for field, label in RATE_FIELDS:
            records.append(
                {
                    "canal": channel_label(getattr(row, "channel", "")),
                    "passage": label,
                    "taux": 100.0 * float(getattr(row, field, 0.0) or 0.0),
                }
            )
    frame = pd.DataFrame(records)
    if frame.empty:
        frame = pd.DataFrame({"canal": [], "passage": [], "taux": []})

    labels = [label for _, label in RATE_FIELDS]
    chart = (
        alt.Chart(frame)
        .mark_bar(height=11, cornerRadiusEnd=3)
        .encode(
            y=alt.Y("canal:N", title=None),
            yOffset=alt.YOffset("passage:N", sort=labels),
            x=alt.X("taux:Q", title="Taux (%)"),
            color=alt.Color(
                "passage:N",
                sort=labels,
                scale=alt.Scale(domain=labels, range=list(tokens.categorical[:3])),
                legend=alt.Legend(title=None, orient="top", columns=3),
            ),
            tooltip=[
                alt.Tooltip("canal:N", title="Canal"),
                alt.Tooltip("passage:N", title="Passage"),
                alt.Tooltip("taux:Q", title="Taux %", format=".2f"),
            ],
        )
    )
    channels = frame["canal"].nunique() if not frame.empty else 1
    return finalize(chart, tokens, title=title, height=max(220, 58 * channels))


# ------------------------------------------------------------------- content


def content_scatter(
    rows: Sequence[object],
    tokens: Tokens,
    *,
    gap_ids: Sequence[str] = (),
    title: str = "Portée et conversion Premium par contenu",
) -> alt.LayerChart:
    """Reach against Premium rate, one point per content unit.

    Emphasis rather than categorical: the flagged gaps take a status colour and
    a label, everything else recedes to the de-emphasis grey. The full values
    live in the table beneath, so nothing depends on reading a dot.
    """
    flagged = set(gap_ids)
    frame = pd.DataFrame(
        [
            {
                "contenu": getattr(row, "title", "") or getattr(row, "content_id", ""),
                "sujet": topic_label(getattr(row, "topic", "")),
                "portee": int(getattr(row, "reach", 0) or 0),
                "premium": 100.0 * float(getattr(row, "premium_rate", 0.0) or 0.0),
                "inscriptions": int(getattr(row, "signups", 0) or 0),
                "etat": (
                    "Portée élevée, conversion faible"
                    if getattr(row, "content_id", "") in flagged
                    else "Reste du catalogue"
                ),
            }
            for row in rows
        ]
    )
    if frame.empty:
        frame = pd.DataFrame(
            {"contenu": [], "sujet": [], "portee": [], "premium": [], "inscriptions": [], "etat": []}
        )

    states = ["Portée élevée, conversion faible", "Reste du catalogue"]
    points = (
        alt.Chart(frame)
        .mark_point(filled=True, stroke=tokens.surface, strokeWidth=2, opacity=0.9)
        .encode(
            x=alt.X("portee:Q", title="Portée (vues) →", scale=alt.Scale(zero=False, nice=True)),
            y=alt.Y("premium:Q", title="Taux Premium % →", scale=alt.Scale(zero=False, nice=True)),
            size=alt.Size(
                "inscriptions:Q",
                scale=alt.Scale(range=[70, 620]),
                legend=alt.Legend(title="Inscriptions", orient="right"),
            ),
            color=alt.Color(
                "etat:N",
                sort=states,
                scale=alt.Scale(domain=states, range=[tokens.serious, tokens.series_muted]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("contenu:N", title="Contenu"),
                alt.Tooltip("sujet:N", title="Sujet"),
                alt.Tooltip("portee:Q", title="Portée", format=",.0f"),
                alt.Tooltip("premium:Q", title="Taux Premium %", format=".2f"),
                alt.Tooltip("inscriptions:Q", title="Inscriptions", format=",.0f"),
            ],
        )
    )
    called_out = (
        alt.Chart(frame)
        .transform_filter(alt.datum.etat == states[0])
        .mark_text(dy=-18, fontSize=10, font=FONT, fontWeight=600, color=tokens.ink_soft)
        .encode(x=alt.X("portee:Q"), y=alt.Y("premium:Q"), text=alt.Text("contenu:N"))
    )
    return finalize(points + called_out, tokens, title=title, height=380)


def topic_chart(
    topics: Sequence[object],
    tokens: Tokens,
    *,
    title: str = "Score de valeur moyen par sujet",
) -> alt.LayerChart:
    """Average Content Value Score per topic — one measure, one colour."""
    frame = pd.DataFrame(
        [
            {
                "sujet": topic_label(getattr(row, "topic", "")),
                "score": round(float(getattr(row, "avg_content_value_score", 0.0) or 0.0), 4),
                "contenus": int(getattr(row, "content_count", 0) or 0),
                "portee": int(getattr(row, "total_reach", 0) or 0),
            }
            for row in topics
        ]
    )
    if frame.empty:
        frame = pd.DataFrame({"sujet": [], "score": [], "contenus": [], "portee": []})
    frame = frame.sort_values("score", ascending=False).reset_index(drop=True)
    order = frame["sujet"].tolist()

    y = alt.Y("sujet:N", sort=order, title=None)
    bars = (
        alt.Chart(frame)
        .mark_bar(height=20, cornerRadiusEnd=4, color=tokens.series)
        .encode(
            y=y,
            x=alt.X("score:Q", title="Score de valeur (0–1)"),
            tooltip=[
                alt.Tooltip("sujet:N", title="Sujet"),
                alt.Tooltip("score:Q", title="Score moyen", format=".3f"),
                alt.Tooltip("contenus:Q", title="Contenus", format=",.0f"),
                alt.Tooltip("portee:Q", title="Portée cumulée", format=",.0f"),
            ],
        )
    )
    labels = (
        alt.Chart(frame)
        .transform_calculate(etiquette="format(datum.score, '.3f')")
        .mark_text(align="left", dx=8, fontSize=11, font=FONT, color=tokens.ink_soft)
        .encode(y=y, x=alt.X("score:Q"), text=alt.Text("etiquette:N"))
    )
    return finalize(bars + labels, tokens, title=title, height=max(200, 42 * len(order)))


def anomaly_table(anomalies: Sequence[object]) -> pd.DataFrame:
    """Table twin for :func:`trend_chart` — the WCAG-clean way to read it."""
    return pd.DataFrame(
        [
            {
                "Jour": getattr(point, "label", ""),
                "Valeur": fmt_int(getattr(point, "value", 0)),
                "Sens": "hausse" if getattr(point, "direction", "") == "up" else "baisse",
                "Méthode": str(getattr(getattr(point, "method", ""), "value", "")),
                "Score": round(float(getattr(point, "score", 0.0)), 3),
            }
            for point in anomalies
        ]
    )
