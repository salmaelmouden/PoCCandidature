"""Presentation helpers for the funnel-entry-point page — pure, no Streamlit runtime.

Kept out of the page module so they can be unit-tested: importing a Streamlit page
executes it.

One decision drives most of this file. The three states a video can be in —
link visible, link behind "plus", no link at all — are **mutually exclusive and
exhaustive**, so they are drawn as a part-to-whole stack rather than as three
separate bars. A reader's question here is "how much of the catalogue offers no
door", and that is a share of the whole, not three unrelated magnitudes.
"""

from __future__ import annotations

from dataclasses import dataclass

import altair as alt
import pandas as pd

from app.skills.cta_analysis import (
    FOLD_LINES,
    THIN_SLICE,
    CtaReport,
    LinkKind,
    PlacementStat,
    TrackingState,
)
from app.skills.public_signal_analysis import VideoFormat
from dashboard.charts import FONT, finalize
from dashboard.formatting import fmt_compact, fmt_int, fmt_pct
from dashboard.theme import LIGHT_TOKENS, Tokens

VISIBLE = "Lien visible"
FOLDED = "Lien à déplier"
ABSENT = "Aucun lien"
STATES: tuple[str, ...] = (VISIBLE, FOLDED, ABSENT)

FORMAT_FR: dict[str, str] = {
    VideoFormat.SHORT.value: "Shorts",
    VideoFormat.LONG.value: "Format long",
}

KIND_FR: dict[LinkKind, str] = {
    LinkKind.PRODUCT: "produit",
    LinkKind.PLATFORM: "plateforme",
    LinkKind.SOCIAL: "réseau social",
}

TRACKING_FR: dict[TrackingState, str] = {
    TrackingState.TRACKED: "Paramètre de campagne visible",
    TrackingState.OPAQUE: "Redirection — non lisible de l'extérieur",
    TrackingState.UNTRACKED: "Aucun paramètre",
}

WATCH_URL = "https://www.youtube.com/watch?v="


@dataclass(frozen=True)
class Headline:
    """One called-out number: what it measures, its value, and what it implies."""

    label: str
    value: str
    note: str


def slice_label(value: str) -> str:
    """French label for a format key; a year is already its own label."""
    return FORMAT_FR.get(value, value)


def headlines(report: CtaReport) -> tuple[Headline, ...]:
    """The three numbers the page is about.

    Coverage first, because it bounds the rest. Then the view-weighted share,
    because a count of videos and a share of audience are two different findings
    and the second is the one an editorial meeting acts on. Attribution last:
    it is the only one that is about instrumentation rather than editorial.
    """
    coverage = report.coverage
    overall = report.overall

    cards = [
        Headline(
            label="Vidéos avec un lien produit",
            value=fmt_pct(overall.share_with_primary, 0),
            note=(
                f"{fmt_int(coverage.with_primary)} sur {fmt_int(coverage.videos_total)}. "
                f"Domaine retenu : {coverage.primary_domain or '—'}."
            ),
        ),
        Headline(
            label="Vues sans porte d'entrée",
            value=fmt_pct(1 - overall.view_share_with_primary, 0),
            note=(
                f"{fmt_compact(overall.views - overall.views_with_primary)} vues cumulées "
                "sur une vidéo qui ne propose aucun lien. Vues à vie, pas des "
                "impressions sur une période."
            ),
        ),
    ]

    if overall.with_primary:
        cards.append(
            Headline(
                label="Liens attribuables",
                value=fmt_pct(overall.share_tracked, 0),
                note=(
                    f"{fmt_int(overall.tracked)} des {fmt_int(overall.with_primary)} liens "
                    "portent un paramètre de campagne lisible. Sans lui, l'entonnoir "
                    "YouTube → inscription ne se mesure pas depuis le lien."
                ),
            )
        )
    return tuple(cards)


def state_frame(rows: list[PlacementStat]) -> pd.DataFrame:
    """Long-form frame: one row per (slice, state), with counts and shares.

    Shares are of the slice for all three states — including ``above_fold``,
    which the report stores against the videos that carry a link. Converting it
    here keeps the three parts summing to the whole, which is the only way the
    stack means anything.
    """
    records = [
        {
            "tranche": slice_label(row.value),
            "etat": state,
            "videos": count,
            "part": round(100 * count / row.videos, 2) if row.videos else 0.0,
            "n": row.videos,
            "mince": row.is_thin,
        }
        for row in rows
        for state, count in (
            (VISIBLE, row.above_fold),
            (FOLDED, row.with_primary - row.above_fold),
            (ABSENT, row.videos - row.with_primary),
        )
    ]
    return pd.DataFrame(records)


def state_stack(
    rows: list[PlacementStat],
    title: str,
    tokens: Tokens = LIGHT_TOKENS,
    *,
    order: list[str] | None = None,
) -> alt.LayerChart:
    """Part-to-whole stack: where the entry point sits, slice by slice.

    An ordinal ramp, not a categorical set: the three states are ordered by how
    reachable the link is. Absence takes the de-emphasis grey rather than a step
    on the ramp — "nothing here" is not a degree of green.
    """
    frame = state_frame(rows)
    stack_order = order or (frame["tranche"].drop_duplicates().tolist() if not frame.empty else [])
    colours = [tokens.funnel_ramp[4], tokens.funnel_ramp[1], tokens.series_muted]

    y = alt.Y("tranche:N", sort=stack_order, title=None)
    bars = (
        alt.Chart(frame)
        .mark_bar(height=24, cornerRadiusEnd=3)
        .encode(
            y=y,
            x=alt.X(
                "part:Q",
                title="Part des vidéos de la tranche (%)",
                scale=alt.Scale(domain=[0, 100]),
                stack="zero",
            ),
            color=alt.Color(
                "etat:N",
                sort=list(STATES),
                scale=alt.Scale(domain=list(STATES), range=colours),
                legend=alt.Legend(title=None, orient="top", columns=3),
            ),
            order=alt.Order("couleur_ordre:Q"),
            tooltip=[
                alt.Tooltip("tranche:N", title="Tranche"),
                alt.Tooltip("etat:N", title="État"),
                alt.Tooltip("videos:Q", title="Vidéos", format=",.0f"),
                alt.Tooltip("part:Q", title="Part %", format=".1f"),
                alt.Tooltip("n:Q", title="Vidéos dans la tranche", format=",.0f"),
            ],
        )
        .transform_calculate(
            couleur_ordre=(
                f"datum.etat === '{VISIBLE}' ? 0 : datum.etat === '{FOLDED}' ? 1 : 2"
            )
        )
    )
    # Only the "no link" share is direct-labelled: it is the number the page
    # argues about, and labelling all three turns a clean stack into confetti.
    # It sits inside the right end of the bar, which is that segment — `ink` over
    # `series_muted` clears contrast in both modes, unlike ink over the ramp.
    labels = (
        alt.Chart(frame)
        .transform_filter(alt.datum.etat == ABSENT)
        .transform_calculate(etiquette="format(datum.part, '.0f') + ' %'")
        .mark_text(align="right", dx=-8, fontSize=11, font=FONT, fontWeight=600, color=tokens.ink)
        .encode(y=y, x=alt.datum(100), text=alt.Text("etiquette:N"))
    )
    height = max(180, 46 * max(len(stack_order), 1))
    return finalize(bars + labels, tokens, title=title, height=height)


def coverage_frame(rows: list[PlacementStat]) -> pd.DataFrame:
    """Table twin for the stack, plus the threshold-free number.

    ``Position médiane`` is there because "above the fold" rests on an
    approximation of where YouTube cuts. The median character offset does not:
    it is the same evidence without the threshold, so a reader who rejects the
    threshold still has something to read.
    """
    return pd.DataFrame(
        [
            {
                "Tranche": slice_label(row.value) + (" *" if row.is_thin else ""),
                "n": row.videos,
                "Avec lien %": round(100 * row.share_with_primary, 1),
                "Visible %": round(100 * row.share_above_fold, 1),
                "Attribuable %": round(100 * row.share_tracked, 1),
                "Position médiane": (
                    round(row.median_offset) if row.median_offset is not None else None
                ),
                "Vues sans lien %": round(100 * (1 - row.view_share_with_primary), 1),
            }
            for row in rows
        ]
    )


def domain_frame(report: CtaReport) -> pd.DataFrame:
    """Every linked domain, with why it could or could not be the product one.

    The excluded domains stay in the table. The page picks its primary domain by
    frequency, and a reader can only audit that choice if the rejected
    candidates are visible next to it.
    """
    return pd.DataFrame(
        [
            {
                "Domaine": row.domain,
                "Type": KIND_FR.get(row.kind, row.kind.value),
                "Vidéos": row.videos,
                "Part du catalogue %": round(100 * row.share_of_catalogue, 1),
                "Retenu": row.domain == report.coverage.primary_domain,
            }
            for row in report.domains
        ]
    )


def wording_frame(report: CtaReport) -> pd.DataFrame:
    """The call-to-action wordings actually used, most frequent first."""
    return pd.DataFrame(
        [
            {"Formulation": row.template, "Vidéos": row.videos}
            for row in report.cta_lines
        ]
    )


def tracking_frame(report: CtaReport) -> pd.DataFrame:
    """Attribution split, keeping "not readable" apart from "not there"."""
    counted = {state: 0 for state in TRACKING_FR}
    for placement in report.placements:
        if placement.has_primary and placement.tracking in counted:
            counted[placement.tracking] += 1
    total = sum(counted.values())
    return pd.DataFrame(
        [
            {
                "État du lien": label,
                "Vidéos": counted[state],
                "Part %": round(100 * counted[state] / total, 1) if total else 0.0,
            }
            for state, label in TRACKING_FR.items()
        ]
    )


def missing_frame(report: CtaReport, *, limit: int = 10) -> pd.DataFrame:
    """The most-watched videos offering no entry point — the actionable list.

    Sorted by views rather than by recency: a five-year-old video that still
    accumulates views is a door that stays shut every day, and it costs one line
    of description to open.
    """
    rows = sorted(
        (item for item in report.placements if not item.has_primary),
        key=lambda item: -item.views,
    )[:limit]
    return pd.DataFrame(
        [
            {
                "Vidéo": item.title,
                "Format": slice_label(item.video_format.value),
                "Année": item.published_year,
                "Vues": item.views,
                "Lien": f"{WATCH_URL}{item.youtube_video_id}",
            }
            for item in rows
        ]
    )


def fold_sentence(report: CtaReport) -> str:
    """One sentence stating the threshold the page uses, in the page's own words."""
    overall = report.overall
    if not overall.with_primary:
        return (
            "Aucun lien produit dans le catalogue : la question de sa visibilité "
            "ne se pose pas encore."
        )
    position = (
        f"la position médiane du premier lien est le caractère "
        f"{round(overall.median_offset)}"
        if overall.median_offset is not None
        else "la position médiane du premier lien n'est pas calculable"
    )
    return (
        f"« Visible » signifie ici : le lien apparaît dans les {FOLD_LINES} premières "
        f"lignes rendues, avant que YouTube ne replie la description. Le seuil est une "
        f"approximation — le point de coupe réel dépend du client et de la largeur de "
        f"l'écran. Sans aucun seuil, {position}, "
        f"sur {fmt_int(overall.with_primary)} vidéos qui en portent un."
    )


def teaser_sentence(report: CtaReport) -> str | None:
    """One line for the landing page, or None when there is no door to talk about.

    Derived from the same report as the full page, for the same reason the rest
    of the brief is: a summary that carries its own copy of a number is a summary
    that will one day disagree with the analysis it summarises.
    """
    overall = report.overall
    domain = report.coverage.primary_domain
    if domain is None or not overall.views:
        return None
    return (
        f"**{fmt_pct(1 - overall.view_share_with_primary, 0)}** des vues cumulées du "
        f"catalogue se produisent sur une vidéo qui ne propose aucun lien vers "
        f"`{domain}`, et **{fmt_pct(1 - overall.share_tracked, 0)}** des liens existants "
        f"ne portent aucun paramètre de campagne lisible de l'extérieur — ce qui "
        f"rend l'entonnoir YouTube → inscription invisible depuis le lien lui-même."
    )


def thin_note(rows: list[PlacementStat]) -> str | None:
    """Which slices are too small to carry a rule, or None when none are."""
    thin = [slice_label(row.value) for row in rows if row.is_thin]
    if not thin:
        return None
    return (
        f"Tranches sous {THIN_SLICE} vidéos, marquées d'un astérisque et lues comme "
        f"une indication, pas comme une règle : {', '.join(thin)}."
    )


def view_weight_sentence(report: CtaReport) -> str:
    """The audience-weighted reading, with the caveat attached rather than nearby."""
    overall = report.overall
    missing_views = overall.views - overall.views_with_primary
    return (
        f"Pondérée par l'audience plutôt que par le nombre de vidéos, la lecture "
        f"change d'échelle : **{fmt_compact(missing_views)} vues cumulées** — "
        f"**{fmt_pct(1 - overall.view_share_with_primary, 0)}** du total — se produisent "
        f"sur une vidéo qui ne propose aucun lien. Ce sont des vues à vie, accumulées "
        f"depuis {report.period_start:%Y}, pas un trafic sur une période : le chiffre "
        f"dit où se trouve l'audience du catalogue, pas combien de personnes ont vu "
        f"quoi ce mois-ci."
    )


def format_gap_sentence(report: CtaReport) -> str | None:
    """The Shorts-versus-long comparison, or None when one side is missing.

    The closing line is **derived**, not written: it only appears when the
    format carrying the most cumulated views is also the one linking least.
    Hard-coding it would be the same failure the rest of this project spends its
    time avoiding — a sentence that keeps asserting yesterday's catalogue.
    """
    by_value = {row.value: row for row in report.by_format}
    short = by_value.get(VideoFormat.SHORT.value)
    long = by_value.get(VideoFormat.LONG.value)
    if short is None or long is None or not short.videos or not long.videos:
        return None

    short_view_share = short.views / max(report.overall.views, 1)
    least_linked = min((short, long), key=lambda row: row.share_with_primary)
    most_watched = max((short, long), key=lambda row: row.views)
    closing = (
        " Le format le plus vu est celui qui ouvre le moins de portes."
        if least_linked is most_watched
        else ""
    )
    return (
        f"**Format long — {fmt_pct(long.share_with_primary, 0)}** des "
        f"{fmt_int(long.videos)} vidéos portent un lien produit. "
        f"**Shorts — {fmt_pct(short.share_with_primary, 0)}** des "
        f"{fmt_int(short.videos)}, alors que ce format concentre "
        f"{fmt_pct(short_view_share, 0)} des vues cumulées du catalogue.{closing}"
    )
