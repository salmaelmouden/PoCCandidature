"""Presentation helpers for the public-catalogue page — pure, no Streamlit runtime.

Kept out of the page module so they can be unit-tested: importing a Streamlit page
executes it.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from app.skills.public_signal_analysis import DimensionStat

SHORT = "Shorts"
LONG = "Format long"
C_SHORT = "#2a78d6"
C_LONG = "#eb6834"
C_MUTED = "#79848f"
C_INK = "#4a5462"
THIN_THRESHOLD = 10

TOPIC_FR = {
    "etf_gestion_passive": "ETF / gestion passive",
    "bourse_actions": "Bourse & actions",
    "education_financiere": "Éducation financière",
    "retraite": "Retraite",
    "immobilier": "Immobilier",
    "interview": "Interview",
    "macro_actualite": "Macro & actualité",
    "portrait_histoire": "Portrait & récit",
    "crypto": "Crypto",
    "fiscalite": "Fiscalité",
    "epargne_placements": "Épargne & placements",
    "produit_finary": "Produit",
    "entrepreneuriat": "Entrepreneuriat",
}

HOOK_FR = {
    "autorite": "Autorité",
    "promesse": "Promesse",
    "curiosite": "Curiosité",
    "question": "Question",
    "chiffre": "Chiffre",
    "recit": "Récit",
    "contrarian": "Contre-pied",
    "actualite": "Actualité",
}


def label_of(value: str) -> str:
    """French label, falling back to the raw key so a new enum value still renders."""
    return TOPIC_FR.get(value, HOOK_FR.get(value, value))


def humanize_age(seconds: float | None) -> str:
    """
    Age in French, with minute resolution.

    Hour-only wording made a 15-minute refresh read as "moins d'1 h" forever,
    which is exactly as uninformative as showing nothing.
    """
    if seconds is None:
        return "—"
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "à l'instant"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"il y a {minutes} min"
    hours = int(seconds // 3600)
    if hours < 24:
        remainder = int((seconds % 3600) // 60)
        return f"il y a {hours} h" if remainder == 0 else f"il y a {hours} h {remainder:02d}"
    days = int(seconds // 86400)
    return "il y a 1 jour" if days == 1 else f"il y a {days} jours"


def fr(value: float, digits: int = 2) -> str:
    """French decimal notation."""
    return f"{value:.{digits}f}".replace(".", ",")


def pick(rows: list[DimensionStat], value: str) -> DimensionStat | None:
    return next((row for row in rows if row.value == value), None)


def rank_of(rows: list[DimensionStat], value: str) -> int | None:
    """1-based rank. Rows arrive sorted by reach index, descending."""
    for position, row in enumerate(rows, start=1):
        if row.value == value:
            return position
    return None


def paired_frame(
    short_rows: list[DimensionStat], long_rows: list[DimensionStat]
) -> pd.DataFrame:
    """
    Values present in **both** formats, with the long-minus-short reach gap.

    Values reported in only one format are dropped: a dumbbell needs two ends.
    """
    shorts = {row.value: row for row in short_rows}
    longs = {row.value: row for row in long_rows}
    records = [
        {
            "cle": key,
            "categorie": label_of(key),
            "ecart": round(longs[key].median_reach_index - shorts[key].median_reach_index, 4),
            "portee_short": shorts[key].median_reach_index,
            "portee_long": longs[key].median_reach_index,
            "n_short": shorts[key].videos,
            "n_long": longs[key].videos,
            "eng_short": shorts[key].median_engagement_rate * 100,
            "eng_long": longs[key].median_engagement_rate * 100,
            "mince": shorts[key].videos < THIN_THRESHOLD or longs[key].videos < THIN_THRESHOLD,
        }
        for key in sorted(shorts.keys() & longs.keys())
    ]
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return frame.sort_values("ecart", ascending=False).reset_index(drop=True)


def table_frame(rows: list[DimensionStat], with_share: bool) -> pd.DataFrame:
    """Evidence table for one dimension. Thin rows are marked, never hidden."""
    return pd.DataFrame(
        [
            {
                "Catégorie": label_of(row.value)
                + (" *" if row.videos < THIN_THRESHOLD else ""),
                "n": row.videos,
                "Portée": round(row.median_reach_index, 2),
                "Engagement %": round(row.median_engagement_rate * 100, 2),
                **(
                    {"Part du corpus %": round(row.share_of_catalogue * 100, 1)}
                    if with_share
                    else {}
                ),
            }
            for row in rows
        ]
    )


def dumbbell(frame: pd.DataFrame, title: str) -> alt.LayerChart:
    """Paired dot plot: one row per category, one dot per format, sorted by gap."""
    order = frame["categorie"].tolist()
    melted = pd.concat(
        [
            frame.assign(
                format=SHORT,
                portee=frame["portee_short"],
                n=frame["n_short"],
                engagement=frame["eng_short"],
            ),
            frame.assign(
                format=LONG,
                portee=frame["portee_long"],
                n=frame["n_long"],
                engagement=frame["eng_long"],
            ),
        ],
        ignore_index=True,
    )[["categorie", "format", "portee", "n", "engagement"]]

    base_y = alt.Y("categorie:N", sort=order, title=None)
    scale = alt.Scale(zero=False, nice=True)

    connector = (
        alt.Chart(frame)
        .mark_rule(strokeWidth=2, opacity=0.32, color=C_MUTED)
        .encode(
            y=base_y,
            x=alt.X("portee_short:Q", scale=scale, title="Indice de portée"),
            x2="portee_long:Q",
        )
    )
    reference = (
        alt.Chart(pd.DataFrame({"x": [1.0]}))
        .mark_rule(strokeDash=[3, 3], color=C_MUTED)
        .encode(x="x:Q")
    )
    points = (
        alt.Chart(melted)
        .mark_point(filled=True, size=150, stroke="white", strokeWidth=2)
        .encode(
            y=base_y,
            x=alt.X("portee:Q", scale=scale),
            color=alt.Color(
                "format:N",
                scale=alt.Scale(domain=[SHORT, LONG], range=[C_SHORT, C_LONG]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("categorie:N", title="Catégorie"),
                alt.Tooltip("format:N", title="Format"),
                alt.Tooltip("portee:Q", title="Portée", format=".2f"),
                alt.Tooltip("engagement:Q", title="Engagement %", format=".2f"),
                alt.Tooltip("n:Q", title="Vidéos"),
            ],
        )
    )
    gaps = (
        alt.Chart(frame)
        .transform_calculate(
            outer="max(datum.portee_short, datum.portee_long)",
            etiquette="(datum.ecart >= 0 ? '+' : '') + format(datum.ecart, '.2f')",
        )
        .mark_text(align="left", dx=10, fontSize=11, color=C_MUTED)
        .encode(y=base_y, x=alt.X("outer:Q", scale=scale), text=alt.Text("etiquette:N"))
    )
    return (
        (connector + reference + points + gaps)
        .properties(height=max(240, 34 * len(order)), title=title)
        .configure_view(strokeWidth=0)
    )


def scatter(rows: list[DimensionStat], title: str) -> alt.LayerChart:
    """Reach against engagement, one point per category, sized by sample."""
    frame = pd.DataFrame(
        [
            {
                "categorie": label_of(row.value),
                "portee": row.median_reach_index,
                "engagement": row.median_engagement_rate * 100,
                "n": row.videos,
            }
            for row in rows
        ]
    )
    points = (
        alt.Chart(frame)
        .mark_point(filled=True, stroke="white", strokeWidth=2, opacity=0.85, color=C_LONG)
        .encode(
            x=alt.X(
                "portee:Q",
                scale=alt.Scale(zero=False, nice=True),
                title="Indice de portée →",
            ),
            y=alt.Y(
                "engagement:Q",
                scale=alt.Scale(zero=False, nice=True),
                title="Taux d'engagement % →",
            ),
            size=alt.Size("n:Q", scale=alt.Scale(range=[80, 900]), legend=None),
            tooltip=[
                alt.Tooltip("categorie:N", title="Sujet"),
                alt.Tooltip("portee:Q", title="Portée", format=".2f"),
                alt.Tooltip("engagement:Q", title="Engagement %", format=".2f"),
                alt.Tooltip("n:Q", title="Vidéos"),
            ],
        )
    )
    labels = points.mark_text(dy=-20, fontSize=11, color=C_INK).encode(
        text="categorie:N", size=alt.value(11)
    )
    reference = (
        alt.Chart(pd.DataFrame({"x": [1.0]}))
        .mark_rule(strokeDash=[3, 3], color=C_MUTED)
        .encode(x="x:Q")
    )
    return (
        (reference + points + labels)
        .properties(height=440, title=title)
        .configure_view(strokeWidth=0)
    )
