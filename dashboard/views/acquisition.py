"""Acquisition — contribution de chaque canal à l'entonnoir.

Présentation uniquement : tout est lu depuis `app.services.dashboard`.
"""

from __future__ import annotations

import streamlit as st

from app.services.dashboard import get_acquisition
from dashboard import charts, components
from dashboard.db import db_session
from dashboard.ui import (
    active_tokens,
    channel_label,
    chart,
    data_provenance_banner,
    fmt_int,
    fmt_pct,
    fmt_period,
    page_header,
    section,
    sidebar_filters,
)

days, _channel = sidebar_filters()
tokens = active_tokens()

with db_session() as session:
    snap = get_acquisition(session, days=days)

page_header(
    "Acquisition",
    "Ce que chaque canal apporte en volume, et là où chacun convertit ou décroche.",
    chips=(
        (fmt_period(snap.period.start, snap.period.end), False),
        (f"{len(snap.rows)} canaux", False),
        (f"{days} jours glissants", True),
    ),
)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)

if not snap.rows:
    st.warning(
        "Aucune ligne d'acquisition sur cette période. Lance `make seed` ou une "
        "ingestion avant d'ouvrir cette page.",
        icon="⚠️",
    )
    st.stop()

st.caption(
    "Le filtre **Canal** de la barre latérale ne s'applique pas ici : cette page "
    "compare les canaux entre eux, elle a donc besoin de tous."
)

# ---- résumé ---------------------------------------------------------------

top = snap.rows[0]
total_signups = sum(row.signups for row in snap.rows) or 1
best_premium = max(snap.rows, key=lambda row: row.premium_rate)

c1, c2, c3 = st.columns(3, gap="medium")
c1.markdown(
    components.insight_card(
        "Premier contributeur",
        channel_label(top.channel),
        note=f"{fmt_int(top.signups)} inscriptions, soit "
        f"{fmt_pct(top.signups / total_signups)} du total de la période.",
        badge_text="Volume",
        badge_kind="fact",
        meter_ratio=top.signups / total_signups,
        meter_color=tokens.series,
        meter_label=fmt_pct(top.signups / total_signups),
    ),
    unsafe_allow_html=True,
)
c2.markdown(
    components.insight_card(
        "Meilleure conversion Premium",
        channel_label(best_premium.channel),
        note=f"{fmt_pct(best_premium.premium_rate)} des utilisateurs activés passent "
        "au Premium — le taux le plus élevé de la période.",
        badge_text="Qualité",
        badge_kind="good",
        meter_ratio=best_premium.premium_rate,
        meter_color=tokens.good,
        meter_label=fmt_pct(best_premium.premium_rate),
    ),
    unsafe_allow_html=True,
)
c3.markdown(
    components.insight_card(
        "Inscriptions, tous canaux",
        fmt_int(total_signups),
        note=f"Réparties sur {len(snap.rows)} canaux, "
        f"du {fmt_period(snap.period.start, snap.period.end)}.",
        badge_text="Total",
        badge_kind="neutral",
    ),
    unsafe_allow_html=True,
)

# ---- 01 · volume ----------------------------------------------------------

section(
    "Qui apporte du volume",
    index="01",
    note="Une seule mesure, donc une seule couleur : assombrir les grandes "
    "barres ne dirait rien que leur longueur ne dise déjà, et les canaux n'ont "
    "pas d'ordre naturel.",
)

metric_label = st.segmented_control(
    "Mesure",
    options=["signups", "views", "visits", "premium_users"],
    default="signups",
    format_func={
        "signups": "Inscriptions",
        "views": "Vues",
        "visits": "Visites",
        "premium_users": "Premium",
    }.get,
    key="acq_metric",
    label_visibility="collapsed",
)
metric = metric_label or "signups"

chart(
    charts.channel_volume_chart(
        snap.rows,
        tokens,
        metric=metric,
        title={
            "signups": "Inscriptions par canal",
            "views": "Vues par canal",
            "visits": "Visites par canal",
            "premium_users": "Utilisateurs Premium par canal",
        }[metric],
    ),
    key="acq_volume",
)

# ---- 02 · taux ------------------------------------------------------------

section(
    "Où chaque canal décroche",
    index="02",
    note="Les trois taux partagent une unité et un axe — ce sont trois passages "
    "du même entonnoir. C'est ce qui permet de voir qu'un canal peut être fort "
    "en haut et faible en bas.",
)

chart(charts.channel_rate_chart(snap.rows, tokens), key="acq_rates")

# ---- tableau --------------------------------------------------------------

section("Le détail", index="03")

st.dataframe(
    [
        {
            "Canal": channel_label(row.channel),
            "Vues": row.views,
            "Visites": row.visits,
            "Inscriptions": row.signups,
            "Activés": row.activated_users,
            "Premium": row.premium_users,
            "Vues → Visites": row.visit_rate,
            "Visites → Inscr.": row.signup_rate,
            "Activés → Premium": row.premium_rate,
        }
        for row in snap.rows
    ],
    width="stretch",
    hide_index=True,
    column_config={
        "Vues": st.column_config.NumberColumn(format="localized"),
        "Visites": st.column_config.NumberColumn(format="localized"),
        "Inscriptions": st.column_config.NumberColumn(format="localized"),
        "Activés": st.column_config.NumberColumn(format="localized"),
        "Premium": st.column_config.NumberColumn(format="localized"),
        "Vues → Visites": st.column_config.ProgressColumn(
            format="percent", min_value=0.0, max_value=1.0
        ),
        "Visites → Inscr.": st.column_config.ProgressColumn(
            format="percent", min_value=0.0, max_value=1.0
        ),
        "Activés → Premium": st.column_config.ProgressColumn(
            format="percent", min_value=0.0, max_value=1.0
        ),
    },
)
