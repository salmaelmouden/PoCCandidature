"""Experiments page — presentation for experiment analyst."""

from __future__ import annotations

import streamlit as st

from app.agents.growth_experiment_analyst_agent import (
    ExperimentAnalystQuestion,
    GrowthExperimentAnalystAgent,
)
from app.agents.growth_experiment_analyst_agent.prompts import (
    DEFAULT_EXPERIMENT_QUESTION,
    DEFAULT_PROPOSE_QUESTION,
)
from dashboard.db import db_session
from dashboard.ui import page_header, sidebar_filters
from app.observability import flush_tracing

EXAMPLE_QUESTIONS = [
    DEFAULT_EXPERIMENT_QUESTION,
    DEFAULT_PROPOSE_QUESTION,
    "Analyze experiment syn_exp_youtube_cta",
]

st.set_page_config(page_title="Experiments · Growth Intelligence AI", layout="wide")
page_header(
    "Experiment analyst",
    "Analyze stored A/B results or propose a test grounded in growth drivers.",
)

days, channel = sidebar_filters()
if "exp_question" not in st.session_state:
    st.session_state.exp_question = DEFAULT_EXPERIMENT_QUESTION

st.caption("Examples")
cols = st.columns(2)
for idx, example in enumerate(EXAMPLE_QUESTIONS):
    if cols[idx % 2].button(example, key=f"exp_ex_{idx}"):
        st.session_state.exp_question = example

question = st.text_area("Question", key="exp_question", height=80)
run = st.button("Run experiment analyst", type="primary")

if run:
    with db_session() as session:
        report = GrowthExperimentAnalystAgent().run(
            session,
            ExperimentAnalystQuestion(question=question, days=days, channel=channel),
        )
    flush_tracing()

    st.caption(f"Mode: `{report.mode.value}`")
    if report.experiment_key:
        st.write(f"Experiment: `{report.experiment_key}`")
    if report.decision_hint:
        st.subheader("Decision hint")
        st.write(report.decision_hint.value)
    if report.design:
        st.subheader("Proposed design")
        st.markdown(f"**{report.design.name}**")
        st.write(report.design.hypothesis)
        st.caption(f"Metric: {report.design.primary_metric}")
        st.write(f"Control: {report.design.control_description}")
        st.write(f"Treatment: {report.design.treatment_description}")
        st.write(f"Success: {report.design.success_criteria}")

    if report.insufficient_evidence:
        st.warning("Insufficient evidence.")

    st.subheader("Claims")
    for claim in report.claims:
        st.markdown(f"**{claim.label.value}** — {claim.text}")
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
        "Synthetic seed includes `syn_exp_youtube_cta`. "
        "Ask whether it worked, or how to test a Premium drop."
    )
