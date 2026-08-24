"""Synthèse — KPI de période, santé de l'entonnoir, anomalies de trafic.

Présentation uniquement : tout est lu depuis `app.services.dashboard`.
"""

from __future__ import annotations

import streamlit as st

from app.services.dashboard import get_overview
from dashboard import charts, components
from dashboard.db import db_session
from dashboard.formatting import stage_short
from dashboard.ui import (
    active_tokens,
    channel_label,
    chart,
    data_provenance_banner,
    fmt_compact,
    fmt_delta,
    fmt_int,
    fmt_pct,
    fmt_period,
    page_header,
    section,
    sidebar_filters,
    table_twin,
)

KPIS: tuple[tuple[str, str], ...] = (
    ("views", "Vues"),
    ("visits", "Visites"),
    ("signups", "Inscriptions"),
    ("premium_users", "Premium"),
)

days, channel = sidebar_filters()
tokens = active_tokens()

with db_session() as session:
    snap = get_overview(session, days=days, channel=channel)

page_header(
    "Synthèse",
    "Les indicateurs de la période, l'endroit où l'entonnoir fuit, et les "
    "journées de trafic qui sortent de l'ordinaire.",
    chips=(
        (fmt_period(snap.period.start, snap.period.end), False),
        (channel_label(channel), False),
        (f"{days} jours glissants", True),
    ),
)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)

st.caption(
    f"Comparé à la période précédente : {fmt_period(snap.period.previous_start, snap.period.previous_end)}."
)

# ---- KPI ------------------------------------------------------------------

columns = st.columns(len(KPIS))
for column, (stage, label) in zip(columns, KPIS, strict=True):
    trend = [value for _, value in snap.daily_series.get(stage, [])]
    column.metric(
        label,
        fmt_compact(snap.current_counts[stage]),
        fmt_delta(snap.relative_deltas[stage]),
        delta_description="vs période précédente",
        help=f"{fmt_int(snap.current_counts[stage])} sur la période "
        f"(précédente : {fmt_int(snap.previous_counts[stage])}).",
        border=True,
        chart_data=trend or None,
        chart_type="area",
    )

# ---- 01 · trafic -----------------------------------------------------------

section(
    "Trafic quotidien",
    index="01",
    note="Une seule série, donc pas de légende. Les points en rouge sont les "
    "journées signalées par la détection d'anomalies ; elles sont aussi listées "
    "en toutes lettres sous le graphique.",
)

chart(
    charts.trend_chart(
        snap.daily_series.get("views", []),
        snap.traffic_anomalies.anomalies,
        tokens,
        title=f"Vues par jour — {channel_label(channel)}",
    ),
    key="overview_trend",
)

anomalies = snap.traffic_anomalies.anomalies
if anomalies:
    st.markdown(
        components.banner(
            f"<strong>{len(anomalies)} journée(s) signalée(s)</strong> sur "
            f"{snap.traffic_anomalies.series_size} — méthode "
            f"<code>{snap.traffic_anomalies.method.value}</code>. Un signalement "
            "est un écart statistique, pas une explication.",
            icon="▲",
        ),
        unsafe_allow_html=True,
    )
    table_twin("Journées signalées — valeurs exactes", charts.anomaly_table(anomalies))
else:
    st.caption("Aucune journée signalée sur cette période.")

# ---- 02 · entonnoir --------------------------------------------------------

section(
    "Santé de l'entonnoir",
    index="02",
    note="Chaque étape est tracée en part des vues, car un entonnoir couvre "
    "plusieurs ordres de grandeur : sur un axe en volumes bruts, tout ce qui "
    "suit la première étape devient un trait. Les volumes réels restent "
    "affichés au bout des barres.",
)

left, right = st.columns([3, 2], gap="medium")

with left:
    chart(
        charts.funnel_chart(snap.current_counts, snap.funnel.conversions, tokens),
        key="overview_funnel",
    )

with right:
    if snap.funnel.bottleneck_from_stage and snap.funnel.bottleneck_dropoff_rate is not None:
        loss = snap.funnel.bottleneck_dropoff_rate
        st.markdown(
            components.insight_card(
                "Point de fuite principal",
                f"{stage_short(snap.funnel.bottleneck_from_stage)} → "
                f"{stage_short(snap.funnel.bottleneck_to_stage or '')}",
                note=f"{fmt_pct(loss)} des volumes se perdent à ce passage — "
                "la plus forte déperdition de l'entonnoir sur la période.",
                badge_text="Déperdition maximale",
                badge_kind="serious" if loss >= 0.8 else "warning",
                meter_ratio=loss,
                meter_color=tokens.serious if loss >= 0.8 else tokens.warning,
                meter_label=fmt_pct(loss),
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            components.insight_card(
                "Point de fuite principal",
                "—",
                note="Aucune étape exploitable pour ce filtre.",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div style="margin-top:.7rem"></div>', unsafe_allow_html=True)
    st.markdown(
        components.insight_card(
            "Des vues au Premium",
            fmt_pct(
                snap.current_counts["premium_users"] / snap.current_counts["views"]
                if snap.current_counts["views"]
                else None,
                2,
            ),
            note="Taux de bout en bout sur la période, tous passages cumulés.",
        ),
        unsafe_allow_html=True,
    )

table_twin(
    "Entonnoir — valeurs exactes",
    [
        {
            "Passage": f"{stage_short(c.from_stage)} → {stage_short(c.to_stage)}",
            "Taux": fmt_pct(c.rate),
            "Depuis": fmt_int(c.from_count),
            "Vers": fmt_int(c.to_count),
        }
        for c in snap.funnel.conversions
    ],
)

st.caption(
    "Les KPI d'entonnoir et de Premium ci-dessus proviennent du jeu synthétique "
    "étiqueté. La page **Catalogue public** est la piste réelle : signaux publics "
    "YouTube, sans aucune inférence d'inscription."
)
