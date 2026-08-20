"""Acquisition page — channel breakdown (presentation only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.services.dashboard import get_acquisition
from dashboard.db import db_session
from dashboard.ui import data_provenance_banner, fmt_pct, page_header, sidebar_filters

st.set_page_config(page_title="Acquisition · Growth Intelligence AI", layout="wide")
page_header("Acquisition", "Channel-level funnel contribution for the selected period.")

days, _channel = sidebar_filters()

with db_session() as session:
    snap = get_acquisition(session, days=days)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)
st.caption(f"Period {snap.period.start} → {snap.period.end}")

if not snap.rows:
    st.warning("No acquisition rows for this period. Run `make seed` or ingest first.")
else:
    frame = pd.DataFrame(
        [
            {
                "channel": row.channel,
                "views": row.views,
                "visits": row.visits,
                "signups": row.signups,
                "activated": row.activated_users,
                "premium": row.premium_users,
                "visit_rate": fmt_pct(row.visit_rate),
                "signup_rate": fmt_pct(row.signup_rate),
                "premium_rate": fmt_pct(row.premium_rate),
            }
            for row in snap.rows
        ]
    )
    st.subheader("By channel")
    st.dataframe(frame, use_container_width=True, hide_index=True)
    chart = frame.set_index("channel")[["views", "signups", "premium"]]
    st.bar_chart(chart)
