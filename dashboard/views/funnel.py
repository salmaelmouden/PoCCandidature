"""Entonnoir — taux de passage, point de fuite, comparaison de périodes.

Présentation uniquement : tout est lu depuis `app.services.dashboard`.
"""

from __future__ import annotations

import streamlit as st

from app.services.dashboard import get_funnel
from dashboard import charts, components
from dashboard.db import db_session
from dashboard.formatting import stage_short, transition_label
from dashboard.ui import (
    active_tokens,
    channel_label,
    chart,
    data_provenance_banner,
    fmt_int,
    fmt_pct,
    fmt_period,
    fmt_points,
    page_header,
    section,
    sidebar_filters,
)

days, channel = sidebar_filters()
tokens = active_tokens()

with db_session() as session:
    snap = get_funnel(session, days=days, channel=channel)

current = snap.comparison.current
previous = snap.comparison.previous

page_header(
    "Entonnoir",
    "Les taux de passage étape par étape, ce qui a bougé depuis la période "
    "précédente, et où se trouve la plus forte déperdition.",
    chips=(
        (fmt_period(snap.period.start, snap.period.end), False),
        (channel_label(channel), False),
        (f"{days} jours glissants", True),
    ),
)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)

st.caption(
    f"Période précédente : {fmt_period(snap.period.previous_start, snap.period.previous_end)}."
)

# ---- 01 · forme de l'entonnoir --------------------------------------------

section(
    "La forme de l'entonnoir",
    index="01",
    note="Chaque étape en part des vues, le volume réel au bout de la barre et "
    "le taux de passage depuis l'étape précédente juste à côté.",
)

left, right = st.columns([3, 2], gap="medium")

with left:
    chart(
        charts.funnel_chart(current.counts.model_dump(), current.conversions, tokens),
        key="funnel_shape",
    )

with right:
    if current.bottleneck_from_stage and current.bottleneck_dropoff_rate is not None:
        loss = current.bottleneck_dropoff_rate
        st.markdown(
            components.insight_card(
                "Point de fuite",
                f"{stage_short(current.bottleneck_from_stage)} → "
                f"{stage_short(current.bottleneck_to_stage or '')}",
                note=f"{fmt_pct(loss)} de déperdition à ce passage.",
                badge_text="Déperdition maximale",
                badge_kind="serious" if loss >= 0.8 else "warning",
                meter_ratio=loss,
                meter_color=tokens.serious if loss >= 0.8 else tokens.warning,
                meter_label=fmt_pct(loss),
            ),
            unsafe_allow_html=True,
        )
    st.markdown('<div style="margin-top:.7rem"></div>', unsafe_allow_html=True)

    worst_move = min(
        (
            (key, value)
            for key, value in snap.comparison.conversion_rate_deltas.items()
            if value is not None
        ),
        key=lambda item: item[1],
        default=None,
    )
    if worst_move is not None:
        key, value = worst_move
        st.markdown(
            components.insight_card(
                "Plus forte dégradation",
                transition_label(key),
                note=f"{fmt_points(value)} par rapport à la période précédente.",
                badge_text="Variation" if value < 0 else "Stable ou en hausse",
                badge_kind="critical" if value < 0 else "good",
            ),
            unsafe_allow_html=True,
        )

# ---- 02 · variation --------------------------------------------------------

section(
    "Ce qui a bougé",
    index="02",
    note="Barres divergentes autour de zéro : la première question ici est un "
    "signe, pas une amplitude. Exprimé en points de pourcentage — jamais en "
    "pourcentage d'un pourcentage.",
)

if any(value is not None for value in snap.comparison.conversion_rate_deltas.values()):
    chart(
        charts.conversion_delta_chart(snap.comparison.conversion_rate_deltas, tokens),
        key="funnel_delta",
    )
else:
    st.markdown(
        components.banner(
            "Pas de période précédente exploitable — aucune variation calculable.",
            icon="◆",
        ),
        unsafe_allow_html=True,
    )

# ---- 03 · détail -----------------------------------------------------------

section("Période courante contre précédente", index="03")

previous_rates = {
    (c.from_stage, c.to_stage): c.rate for c in previous.conversions
}

st.dataframe(
    [
        {
            "Passage": f"{stage_short(c.from_stage)} → {stage_short(c.to_stage)}",
            "Taux courant": c.rate,
            "Taux précédent": previous_rates.get((c.from_stage, c.to_stage)),
            "Variation": (
                c.rate - previous_rates[(c.from_stage, c.to_stage)]
                if (c.from_stage, c.to_stage) in previous_rates
                else None
            ),
            "Depuis": c.from_count,
            "Vers": c.to_count,
        }
        for c in current.conversions
    ],
    width="stretch",
    hide_index=True,
    column_config={
        "Taux courant": st.column_config.ProgressColumn(
            format="percent", min_value=0.0, max_value=1.0
        ),
        "Taux précédent": st.column_config.NumberColumn(format="percent"),
        "Variation": st.column_config.NumberColumn(format="percent"),
        "Depuis": st.column_config.NumberColumn(format="localized"),
        "Vers": st.column_config.NumberColumn(format="localized"),
    },
)

with st.expander("Volumes par étape — courant et précédent"):
    st.dataframe(
        [
            {
                "Étape": stage_short(stage),
                "Courant": getattr(current.counts, stage),
                "Précédent": getattr(previous.counts, stage),
                "Écart": snap.comparison.absolute_deltas.get(stage),
                "Écart relatif": snap.comparison.relative_deltas.get(stage),
            }
            for stage in current.counts.model_dump()
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Courant": st.column_config.NumberColumn(format="localized"),
            "Précédent": st.column_config.NumberColumn(format="localized"),
            "Écart": st.column_config.NumberColumn(format="localized"),
            "Écart relatif": st.column_config.NumberColumn(format="percent"),
        },
    )

st.caption(
    f"Volumes en tête d'entonnoir : {fmt_int(current.counts.views)} vues "
    f"contre {fmt_int(previous.counts.views)} sur la période précédente."
)
