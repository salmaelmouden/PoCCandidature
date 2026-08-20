"""Presentation helpers for the Streamlit dashboard (no analytics math)."""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from app.db.constants import Channel

BRAND = "Growth Intelligence AI"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;600&display=swap');
html, body, [class*="css"]  {
  font-family: "Source Sans 3", sans-serif;
}
.gia-hero {
  background: linear-gradient(135deg, #0f2a24 0%, #1c4a3e 45%, #c4a574 140%);
  color: #f4f7f5;
  padding: 1.6rem 1.8rem;
  border-radius: 0;
  margin-bottom: 1.25rem;
}
.gia-hero h1 {
  font-family: Fraunces, Georgia, serif;
  font-size: 2rem;
  margin: 0 0 0.35rem 0;
  letter-spacing: -0.02em;
}
.gia-hero p { margin: 0; opacity: 0.9; max-width: 42rem; }
.gia-banner {
  border-left: 4px solid #c4a574;
  background: #f3eee4;
  color: #2a241c;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}
div[data-testid="stMetricValue"] { font-family: Fraunces, Georgia, serif; }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    inject_theme()
    st.markdown(
        f'<div class="gia-hero"><h1>{BRAND}</h1><p><strong>{title}</strong> — {subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def data_provenance_banner(*, has_synthetic: bool, labels: Iterable[str]) -> None:
    label_text = ", ".join(sorted(labels)) if labels else "unknown"
    if has_synthetic:
        msg = (
            f"Demo metrics include <strong>labelled synthetic data</strong> "
            f"({label_text}). Not real company data."
        )
    else:
        msg = f"Dataset labels in view: <strong>{label_text}</strong>."
    st.markdown(f'<div class="gia-banner">{msg}</div>', unsafe_allow_html=True)


def sidebar_filters() -> tuple[int, str | None]:
    st.sidebar.header("Filters")
    days = st.sidebar.selectbox("Period (days)", options=[7, 14, 30, 90], index=2)
    channel_options = ["All channels", *[c.value for c in Channel]]
    selected = st.sidebar.selectbox("Channel", options=channel_options, index=0)
    channel = None if selected == "All channels" else selected
    return days, channel


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def fmt_delta(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value * 100:+.1f}%"
