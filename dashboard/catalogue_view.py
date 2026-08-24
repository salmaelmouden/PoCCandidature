"""Presentation helpers for the public-catalogue page — pure, no Streamlit runtime.

Kept out of the page module so they can be unit-tested: importing a Streamlit page
executes it.

The charts here take a :class:`~dashboard.theme.Tokens` so they follow the app
theme, and default to the light set so a caller that only wants a spec — a test,
a static export — does not have to know about themes at all.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from app.skills.public_signal_analysis import DimensionStat
from dashboard.charts import FONT, finalize
from dashboard.formatting import fr, humanize_age  # noqa: F401  (re-exported)
from dashboard.theme import LIGHT_TOKENS, Tokens

SHORT = "Shorts"
LONG = "Format long"
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


def pick(rows: list[DimensionStat], value: str) -> DimensionStat | None:
    return next((row for row in rows if row.value == value), None)


def rank_of(rows: list[DimensionStat], value: str) -> int | None:
    """1-based rank. Rows arrive sorted by reach index, descending."""
    for position, row in enumerate(rows, start=1):
        if row.value == value:
            return position
    return None


def empty_state_message(
    *, has_report: bool, videos: int, classified: int
) -> str | None:
    """The message to show instead of the analysis, or None if it can render.

    The catalogue page is public and unauthenticated. An empty catalogue is an
    ordinary state — on a fresh deploy the refresher has not run its first cycle
    — but the analysis skill rightly refuses to analyse nothing, so something has
    to decide what the visitor sees instead of a stack trace.

    Two empty states, two remedies, and naming the wrong one sends the reader
    after a fix that changes nothing: no videos at all is the refresher's job,
    while videos present but unclassified is the classifier's.

    Lives here rather than in the page because importing a Streamlit page runs
    it, and this decision is worth testing.
    """
    if has_report and classified > 0:
        return None
    if videos == 0:
        return (
            "Catalogue vide — aucune vidéo n'a encore été ingérée.\n\n"
            "- En local : `make ingest-youtube` puis `make classify`.\n"
            "- En production : c'est le service *refresher* qui alimente cette "
            "page (voir `docs/guides/deploy-railway.md` §3). Pour la remplir "
            "immédiatement, un cycle unique suffit : "
            "`python scripts/refresh_catalogue.py`."
        )
    return (
        f"{videos} vidéos ingérées, mais aucune n'est encore classée.\n\n"
        "- En local : `make classify`.\n"
        "- En production : le *refresher* classe à chaque cycle ; si le compte "
        "reste à zéro, vérifie `ANTHROPIC_API_KEY` sur ce service."
    )


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


def dumbbell(
    frame: pd.DataFrame, title: str, tokens: Tokens = LIGHT_TOKENS
) -> alt.LayerChart:
    """Paired dot plot: one row per category, one dot per format, sorted by gap.

    Two series, so the legend stays — and the gap is direct-labelled, which is
    the number the chart is actually about.
    """
    order = frame["categorie"].tolist()
    short_colour, long_colour = tokens.categorical[0], tokens.categorical[1]
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
        .mark_rule(strokeWidth=2, opacity=0.32, color=tokens.axis)
        .encode(
            y=base_y,
            x=alt.X("portee_short:Q", scale=scale, title="Indice de portée"),
            x2="portee_long:Q",
        )
    )
    reference = (
        alt.Chart(pd.DataFrame({"x": [1.0]}))
        .mark_rule(color=tokens.axis, strokeWidth=1)
        .encode(x="x:Q")
    )
    points = (
        alt.Chart(melted)
        .mark_point(filled=True, size=150, stroke=tokens.surface, strokeWidth=2)
        .encode(
            y=base_y,
            x=alt.X("portee:Q", scale=scale),
            color=alt.Color(
                "format:N",
                scale=alt.Scale(domain=[SHORT, LONG], range=[short_colour, long_colour]),
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
        .mark_text(align="left", dx=10, fontSize=11, font=FONT, color=tokens.ink_muted)
        .encode(y=base_y, x=alt.X("outer:Q", scale=scale), text=alt.Text("etiquette:N"))
    )
    return finalize(
        connector + reference + points + gaps,
        tokens,
        title=title,
        height=max(240, 34 * len(order)),
    )


def scatter(
    rows: list[DimensionStat], title: str, tokens: Tokens = LIGHT_TOKENS
) -> alt.LayerChart:
    """Reach against engagement, one point per category, sized by sample.

    A single series, so no legend box: every point is direct-labelled instead.
    """
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
        .mark_point(
            filled=True,
            stroke=tokens.surface,
            strokeWidth=2,
            opacity=0.85,
            color=tokens.categorical[1],
        )
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
    labels = points.mark_text(
        dy=-20, fontSize=11, font=FONT, color=tokens.ink_soft
    ).encode(text="categorie:N", size=alt.value(11))
    reference = (
        alt.Chart(pd.DataFrame({"x": [1.0]}))
        .mark_rule(color=tokens.axis, strokeWidth=1)
        .encode(x="x:Q")
    )
    return finalize(reference + points + labels, tokens, title=title, height=440)
