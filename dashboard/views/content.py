"""Contenu — score de valeur, comparaison des sujets, écarts portée/conversion.

Présentation uniquement : tout est lu depuis `app.services.dashboard`.
"""

from __future__ import annotations

import streamlit as st

from app.services.dashboard import get_content
from dashboard import charts, components
from dashboard.db import db_session
from dashboard.formatting import topic_label
from dashboard.ui import (
    active_tokens,
    channel_label,
    chart,
    data_provenance_banner,
    fmt_int,
    fmt_pct,
    fmt_period,
    fr,
    page_header,
    section,
    sidebar_filters,
)

days, channel = sidebar_filters()
tokens = active_tokens()

with db_session() as session:
    snap = get_content(session, days=days, channel=channel)

page_header(
    "Contenu",
    "Ce qui crée de la valeur, ce qui n'en crée pas, et ce qui touche beaucoup "
    "de monde sans convertir.",
    chips=(
        (fmt_period(snap.period.start, snap.period.end), False),
        (channel_label(channel), False),
        (f"{len(snap.ranked)} contenus classés", True),
    ),
)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)

if not snap.ranked:
    st.warning("Aucun contenu sur cette période.", icon="⚠️")
    st.stop()

# ---- résumé ---------------------------------------------------------------

best = snap.ranked[0]
best_topic = max(snap.topics, key=lambda t: t.avg_content_value_score) if snap.topics else None
gaps = snap.reach_conversion_gaps

c1, c2, c3 = st.columns(3, gap="medium")
c1.markdown(
    components.insight_card(
        "Meilleur contenu",
        best.title,
        note=f"Score {fr(best.score, 3)} · {fmt_int(best.reach)} vues · "
        f"{fmt_pct(best.premium_rate)} de conversion Premium.",
        badge_text="Score de valeur",
        badge_kind="fact",
        meter_ratio=best.score,
        meter_color=tokens.series,
        meter_label=fr(best.score, 3),
    ),
    unsafe_allow_html=True,
)
c2.markdown(
    components.insight_card(
        "Sujet le mieux valorisé",
        topic_label(best_topic.topic) if best_topic else "—",
        note=(
            f"Score moyen {fr(best_topic.avg_content_value_score, 3)} sur "
            f"{best_topic.content_count} contenus."
            if best_topic
            else "Aucun sujet exploitable."
        ),
        badge_text="Moyenne par sujet",
        badge_kind="neutral",
    ),
    unsafe_allow_html=True,
)
c3.markdown(
    components.insight_card(
        "Écarts portée / conversion",
        str(len(gaps)),
        note="Contenus qui circulent bien mais convertissent mal — c'est là que "
        "le levier est le moins cher.",
        badge_text="À regarder" if gaps else "Rien à signaler",
        badge_kind="serious" if gaps else "good",
    ),
    unsafe_allow_html=True,
)

# ---- 01 · classement ------------------------------------------------------

section(
    "Classement par score de valeur",
    index="01",
    note="Le score pondère la portée, l'engagement, la contribution aux "
    "inscriptions et la conversion Premium — il valorise l'aval plutôt que "
    "l'audience brute.",
)

st.dataframe(
    [
        {
            "Contenu": row.title,
            "Sujet": topic_label(row.topic),
            "Score": row.score,
            "Portée": row.reach,
            "Inscriptions": row.signups,
            "Premium": row.premium_users,
            "Taux inscr.": row.signup_rate,
            "Taux Premium": row.premium_rate,
        }
        for row in snap.ranked
    ],
    width="stretch",
    hide_index=True,
    column_config={
        "Score": st.column_config.ProgressColumn(
            format="%.3f", min_value=0.0, max_value=max(1.0, max(r.score for r in snap.ranked))
        ),
        "Portée": st.column_config.NumberColumn(format="localized"),
        "Inscriptions": st.column_config.NumberColumn(format="localized"),
        "Premium": st.column_config.NumberColumn(format="localized"),
        "Taux inscr.": st.column_config.NumberColumn(format="percent"),
        "Taux Premium": st.column_config.NumberColumn(format="percent"),
    },
)

# ---- 02 · portée vs conversion --------------------------------------------

section(
    "Portée contre conversion",
    index="02",
    note="Mise en évidence plutôt que catégories : les contenus signalés portent "
    "une couleur d'alerte et leur titre, le reste du catalogue recule au gris. "
    "Les valeurs exactes sont dans le tableau ci-dessus.",
)

chart(
    charts.content_scatter(
        snap.ranked,
        tokens,
        gap_ids=[gap.content_id for gap in gaps],
    ),
    key="content_scatter",
)

# ---- 03 · sujets ----------------------------------------------------------

section("Comparaison des sujets", index="03")

left, right = st.columns([3, 2], gap="medium")
with left:
    chart(charts.topic_chart(snap.topics, tokens), key="content_topics")
with right:
    st.dataframe(
        [
            {
                "Sujet": topic_label(t.topic),
                "Contenus": t.content_count,
                "Portée": t.total_reach,
                "Inscriptions": t.total_signups,
                "Premium": t.total_premium_users,
                "Taux Premium": t.premium_rate,
            }
            for t in snap.topics
        ],
        width="stretch",
        hide_index=True,
        height=340,
        column_config={
            "Contenus": st.column_config.NumberColumn(format="localized"),
            "Portée": st.column_config.NumberColumn(format="localized"),
            "Inscriptions": st.column_config.NumberColumn(format="localized"),
            "Premium": st.column_config.NumberColumn(format="localized"),
            "Taux Premium": st.column_config.NumberColumn(format="percent"),
        },
    )

# ---- 04 · écarts ----------------------------------------------------------

section(
    "Portée élevée, conversion faible",
    index="04",
    note="Signalé par la compétence d'analyse de contenu, avec la raison qui a "
    "déclenché le signalement.",
)

if not gaps:
    st.markdown(
        components.banner(
            "Aucun écart signalé sur cette période — la portée et la conversion "
            "vont dans le même sens.",
            icon="●",
            live=True,
        ),
        unsafe_allow_html=True,
    )
else:
    st.dataframe(
        [
            {
                "Contenu": gap.title,
                "Sujet": topic_label(gap.topic),
                "Portée": gap.reach,
                "Taux Premium": gap.premium_rate,
                "Score": gap.content_value_score,
                "Motif du signalement": gap.reason,
            }
            for gap in gaps
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Portée": st.column_config.NumberColumn(format="localized"),
            "Taux Premium": st.column_config.NumberColumn(format="percent"),
            "Score": st.column_config.NumberColumn(format="%.3f"),
            "Motif du signalement": st.column_config.TextColumn(width="large"),
        },
    )
