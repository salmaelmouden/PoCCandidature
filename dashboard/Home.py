"""Growth Intelligence AI — Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from dashboard.db import db_session
from dashboard.ui import data_provenance_banner, fmt_delta, page_header, sidebar_filters
from app.services.dashboard import get_overview

st.set_page_config(
    page_title="Growth Intelligence AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

page_header(
    "Executive overview",
    "Period KPIs, funnel health, and traffic anomalies from the analytics layer.",
)
days, channel = sidebar_filters()

with db_session() as session:
    snap = get_overview(session, days=days, channel=channel)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)

st.caption(
    f"Period {snap.period.start} → {snap.period.end} "
    f"(vs {snap.period.previous_start} → {snap.period.previous_end})"
    + (f" · channel={channel}" if channel else "")
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Views", f"{snap.current_counts['views']:,}", fmt_delta(snap.relative_deltas["views"]))
c2.metric("Visits", f"{snap.current_counts['visits']:,}", fmt_delta(snap.relative_deltas["visits"]))
c3.metric(
    "Signups", f"{snap.current_counts['signups']:,}", fmt_delta(snap.relative_deltas["signups"])
)
c4.metric(
    "Premium",
    f"{snap.current_counts['premium_users']:,}",
    fmt_delta(snap.relative_deltas["premium_users"]),
)

st.subheader("Funnel bottleneck")
if snap.funnel.bottleneck_from_stage:
    st.write(
        f"**{snap.funnel.bottleneck_from_stage} → {snap.funnel.bottleneck_to_stage}** "
        f"(dropoff rate {snap.funnel.bottleneck_dropoff_rate:.1%})"
    )
else:
    st.write("No funnel stages available for this filter.")

st.subheader("Traffic anomalies (views)")
anomalies = snap.traffic_anomalies.anomalies
if not anomalies:
    st.write("No anomalies flagged for this period.")
else:
    st.dataframe(
        [
            {
                "date": a.label,
                "value": a.value,
                "direction": a.direction,
                "method": a.method.value,
                "score": round(a.score, 3),
            }
            for a in anomalies
        ],
        use_container_width=True,
        hide_index=True,
    )

st.info(
    "Sidebar: Acquisition · Content · Funnel · Analyst · Orchestrator · Experiments · "
    "**Catalogue public** (real YouTube — no signup inference). "
    "Funnel / Premium KPIs above are labelled synthetic unless you filtered them out."
)
