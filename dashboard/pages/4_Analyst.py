"""AI Growth Analyst page — presentation only; agent owns analysis."""

from __future__ import annotations

import streamlit as st

from app.agents.growth_data_analyst_agent import AnalystQuestion, GrowthDataAnalystAgent
from app.agents.growth_data_analyst_agent.prompts import DEFAULT_PREMIUM_QUESTION
from dashboard.db import db_session
from dashboard.ui import data_provenance_banner, page_header, sidebar_filters

EXAMPLE_QUESTIONS = [
    DEFAULT_PREMIUM_QUESTION,
    "Where is the funnel bottleneck right now?",
    "Which channel is leaking the most at Premium?",
    "Which topics have high reach but low conversion?",
    "What changed in the funnel vs the previous period?",
    "Any traffic anomalies this period?",
]

st.set_page_config(page_title="Analyst · Growth Intelligence AI", layout="wide")
page_header(
    "Data analyst",
    "Structured evidence for “what is happening?” — tools are chosen from your question.",
)

days, channel = sidebar_filters()
if "analyst_question" not in st.session_state:
    st.session_state.analyst_question = DEFAULT_PREMIUM_QUESTION

st.caption("Examples")
cols = st.columns(2)
for idx, example in enumerate(EXAMPLE_QUESTIONS):
    if cols[idx % 2].button(example, key=f"ex_{idx}"):
        st.session_state.analyst_question = example

question = st.text_area("Question", key="analyst_question", height=80)
run = st.button("Run analyst", type="primary")

if run:
    with db_session() as session:
        report = GrowthDataAnalystAgent().run(
            session,
            AnalystQuestion(question=question, days=days, channel=channel),
        )

    labels = set()
    for call in report.tool_calls:
        if call.ok and call.detail.get("dataset_labels"):
            labels.update(call.detail["dataset_labels"])
    has_synthetic = any(
        call.ok and call.detail.get("has_synthetic") for call in report.tool_calls
    )
    data_provenance_banner(has_synthetic=has_synthetic, labels=labels)

    st.caption(f"Period {report.period_start} → {report.period_end}")
    if report.primary_driver:
        st.subheader("Primary driver")
        st.write(report.primary_driver)
    if report.insufficient_evidence:
        st.warning("Insufficient evidence — do not treat this as a complete explanation.")

    st.subheader("Claims")
    for claim in report.claims:
        st.markdown(f"**{claim.label.value}** — {claim.text}")
        if claim.source_tool:
            st.caption(f"source tool: `{claim.source_tool}`")
        if claim.numbers:
            st.json(claim.numbers)

    st.subheader("Tool calls")
    st.dataframe(
        [{"tool": t.tool, "ok": t.ok, "summary": t.summary} for t in report.tool_calls],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "Pick an example or type a question, then run. "
        "Different intents use different tools (bottleneck ≠ content ≠ anomalies)."
    )
