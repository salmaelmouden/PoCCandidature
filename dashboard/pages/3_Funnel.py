"""Funnel page — stage rates and period compare (presentation only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.services.dashboard import get_funnel
from dashboard.db import db_session
from dashboard.ui import data_provenance_banner, fmt_pct, page_header, sidebar_filters

st.set_page_config(page_title="Funnel · Growth Intelligence AI", layout="wide")
page_header("Funnel", "Stage conversion rates, dropoffs, and period-over-period deltas.")

days, channel = sidebar_filters()

with db_session() as session:
    snap = get_funnel(session, days=days, channel=channel)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)
st.caption(f"Period {snap.period.start} → {snap.period.end}")

current = snap.comparison.current
previous = snap.comparison.previous

left, right = st.columns(2)
with left:
    st.subheader("Current period")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "from": c.from_stage,
                    "to": c.to_stage,
                    "rate": fmt_pct(c.rate),
                    "from_count": c.from_count,
                    "to_count": c.to_count,
                }
                for c in current.conversions
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
with right:
    st.subheader("Previous period")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "from": c.from_stage,
                    "to": c.to_stage,
                    "rate": fmt_pct(c.rate),
                    "from_count": c.from_count,
                    "to_count": c.to_count,
                }
                for c in previous.conversions
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Bottleneck (current)")
if current.bottleneck_from_stage:
    st.write(
        f"**{current.bottleneck_from_stage} → {current.bottleneck_to_stage}** "
        f"(dropoff {fmt_pct(current.bottleneck_dropoff_rate)})"
    )

st.subheader("Conversion rate deltas (current − previous)")
st.dataframe(
    pd.DataFrame(
        [
            {"transition": key, "delta": fmt_pct(delta) if delta is not None else "n/a"}
            for key, delta in snap.comparison.conversion_rate_deltas.items()
        ]
    ),
    use_container_width=True,
    hide_index=True,
)
