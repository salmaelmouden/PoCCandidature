"""AI Orchestrator page — primary entrypoint (ADR-004)."""

from __future__ import annotations

import streamlit as st

from app.agents.growth_orchestrator_agent import GrowthOrchestratorAgent, OrchestratorQuestion
from app.agents.growth_orchestrator_agent.prompts import DEFAULT_ORCHESTRATOR_QUESTION
from dashboard.db import db_session
from dashboard.ui import data_provenance_banner, page_header, sidebar_filters
from app.observability import flush_tracing

EXAMPLE_QUESTIONS = [
    DEFAULT_ORCHESTRATOR_QUESTION,
    "What should we do about the Premium conversion drop?",
    "Did the YouTube CTA experiment work?",
    "How should we test the Premium conversion drop?",
    "Where is the funnel bottleneck right now?",
]

st.set_page_config(page_title="Orchestrator · Growth Intelligence AI", layout="wide")
page_header(
    "Growth orchestrator",
    "Primary AI entrypoint — routes to analyst and/or strategist, then synthesizes.",
)

days, channel = sidebar_filters()
if "orch_question" not in st.session_state:
    st.session_state.orch_question = DEFAULT_ORCHESTRATOR_QUESTION

st.caption("Examples")
cols = st.columns(2)
for idx, example in enumerate(EXAMPLE_QUESTIONS):
    if cols[idx % 2].button(example, key=f"orch_ex_{idx}"):
        st.session_state.orch_question = example

question = st.text_area("Question", key="orch_question", height=80)
run = st.button("Run orchestrator", type="primary")

if run:
    with db_session() as session:
        resp = GrowthOrchestratorAgent().run(
            session,
            OrchestratorQuestion(question=question, days=days, channel=channel),
        )
    flush_tracing()

    labels: set[str] = set()
    has_synthetic = False
    if resp.analyst_report:
        for call in resp.analyst_report.tool_calls:
            if call.ok and call.detail.get("dataset_labels"):
                labels.update(call.detail["dataset_labels"])
            if call.ok and call.detail.get("has_synthetic"):
                has_synthetic = True
    data_provenance_banner(has_synthetic=has_synthetic, labels=labels)

    st.caption(
        f"Route: `{resp.route.value}` · agents: {', '.join(resp.agents_called)} · "
        f"{resp.period_start} → {resp.period_end}"
    )
    st.subheader("Summary")
    st.write(resp.summary)
    if resp.insufficient_evidence:
        st.warning("Insufficient evidence from one or more specialists.")

    if resp.analyst_report and resp.analyst_report.primary_driver:
        st.subheader("Primary driver (analyst)")
        st.write(resp.analyst_report.primary_driver)

    if resp.strategy_report and resp.strategy_report.recommendations:
        st.subheader("Recommendations (strategist)")
        for rec in resp.strategy_report.recommendations:
            st.markdown(f"**[{rec.priority.value}] {rec.title}**")
            st.write(rec.action)
            st.caption(rec.rationale)

    if resp.experiment_report:
        st.subheader("Experiment specialist")
        st.caption(f"mode=`{resp.experiment_report.mode.value}`")
        if resp.experiment_report.decision_hint:
            st.write(f"Decision hint: **{resp.experiment_report.decision_hint.value}**")
        if resp.experiment_report.design:
            st.write(resp.experiment_report.design.hypothesis)

    st.subheader("Claims")
    for claim in resp.claims:
        st.markdown(f"**{claim.label.value}** — {claim.text}")
        if claim.source_tool:
            st.caption(f"source: `{claim.source_tool}`")

    with st.expander("Specialist reports (raw)"):
        if resp.analyst_report:
            st.write("Analyst tool calls")
            st.dataframe(
                [
                    {"tool": t.tool, "ok": t.ok, "summary": t.summary}
                    for t in resp.analyst_report.tool_calls
                ],
                use_container_width=True,
                hide_index=True,
            )
        if resp.strategy_report:
            st.write("Strategist tool calls")
            st.dataframe(
                [
                    {"tool": t.tool, "ok": t.ok, "summary": t.summary}
                    for t in resp.strategy_report.tool_calls
                ],
                use_container_width=True,
                hide_index=True,
            )
        if resp.experiment_report:
            st.write("Experiment tool calls")
            st.dataframe(
                [
                    {"tool": t.tool, "ok": t.ok, "summary": t.summary}
                    for t in resp.experiment_report.tool_calls
                ],
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info(
        "Diagnostics → analyst; actions → strategist; experiment/A/B → experiment agent."
    )
