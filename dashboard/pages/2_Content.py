"""Content performance page — ranking and gaps (presentation only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.services.dashboard import get_content
from dashboard.db import db_session
from dashboard.ui import data_provenance_banner, fmt_pct, page_header, sidebar_filters

st.set_page_config(page_title="Content · Growth Intelligence AI", layout="wide")
page_header(
    "Content performance",
    "Content Value Score ranking, topic compare, and reach/conversion gaps.",
)

days, channel = sidebar_filters()

with db_session() as session:
    snap = get_content(session, days=days, channel=channel)

data_provenance_banner(has_synthetic=snap.has_synthetic, labels=snap.dataset_labels)
st.caption(f"Period {snap.period.start} → {snap.period.end}")

if not snap.ranked:
    st.warning("No content units for this period.")
else:
    st.subheader("Top content by Content Value Score")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "content_id": row.content_id,
                    "title": row.title,
                    "topic": row.topic,
                    "score": round(row.score, 4),
                    "reach": row.reach,
                    "signups": row.signups,
                    "premium": row.premium_users,
                    "signup_rate": fmt_pct(row.signup_rate),
                    "premium_rate": fmt_pct(row.premium_rate),
                }
                for row in snap.ranked
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Topics")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "topic": t.topic,
                    "items": t.content_count,
                    "reach": t.total_reach,
                    "signups": t.total_signups,
                    "premium": t.total_premium_users,
                    "avg_cvs": round(t.avg_content_value_score, 4),
                    "signup_rate": fmt_pct(t.signup_rate),
                    "premium_rate": fmt_pct(t.premium_rate),
                }
                for t in snap.topics
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("High reach / low conversion gaps")
    if not snap.reach_conversion_gaps:
        st.write("No gaps flagged.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "content_id": g.content_id,
                        "title": g.title,
                        "topic": g.topic,
                        "reach": g.reach,
                        "premium_rate": fmt_pct(g.premium_rate),
                        "cvs": round(g.content_value_score, 4),
                        "reason": g.reason,
                    }
                    for g in snap.reach_conversion_gaps
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
