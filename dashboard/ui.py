"""Streamlit shell for the dashboard — layout and chrome, never analytics.

Everything that computes lives in `app.services` / `app.skills`; everything that
*renders* a value lives in `dashboard.formatting`, `dashboard.components` or
`dashboard.charts`, which are pure and tested. This module is the thin layer
that hands those results to Streamlit.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import streamlit as st

from app.db.constants import Channel
from dashboard import components
from dashboard.formatting import (  # re-exported: pages import formatters from here
    channel_label,
    fmt_compact,
    fmt_delta,
    fmt_int,
    fmt_pct,
    fmt_period,
    fmt_points,
    fr,
)
from dashboard.theme import Tokens, stylesheet, tokens_for

BRAND = "Growth Intelligence AI"

__all__ = [
    "BRAND",
    "active_tokens",
    "channel_label",
    "chart",
    "data_provenance_banner",
    "fmt_compact",
    "fmt_delta",
    "fmt_int",
    "fmt_pct",
    "fmt_period",
    "fmt_points",
    "fr",
    "inject_theme",
    "page_header",
    "render_claims",
    "section",
    "sidebar_brand",
    "sidebar_filters",
    "table_twin",
]

_PERIOD_OPTIONS: tuple[int, ...] = (7, 14, 30, 90)
_ALL_CHANNELS = "Tous les canaux"


def active_tokens() -> Tokens:
    """Tokens for the theme the viewer is actually in.

    Streamlit exposes the resolved theme rather than the OS preference, so the
    dark palette follows the app's own theme switch instead of second-guessing
    it. Older runtimes without `st.context.theme` fall back to light.
    """
    try:
        return tokens_for(st.context.theme.type)
    except (AttributeError, KeyError):
        return tokens_for(None)


def inject_theme() -> None:
    """Inject the stylesheet. Cheap enough to call more than once per run."""
    st.markdown(stylesheet(active_tokens()), unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.sidebar.markdown(components.sidebar_brand(), unsafe_allow_html=True)


def page_header(
    title: str,
    subtitle: str,
    *,
    chips: Sequence[tuple[str, bool]] = (),
) -> None:
    """Hero banner. `chips` are `(label, is_live)` pairs — period, channel, freshness."""
    st.markdown(
        components.hero(title, subtitle, brand=BRAND, chips=chips),
        unsafe_allow_html=True,
    )


def section(title: str, *, index: str | None = None, note: str | None = None) -> None:
    st.markdown(components.section(title, index=index, note=note), unsafe_allow_html=True)


def data_provenance_banner(*, has_synthetic: bool, labels: Iterable[str]) -> None:
    message = components.provenance_message(has_synthetic=has_synthetic, labels=labels)
    st.markdown(
        components.banner(message, icon="◆" if has_synthetic else "●", live=not has_synthetic),
        unsafe_allow_html=True,
    )


def sidebar_filters() -> tuple[int, str | None]:
    """Period and channel, shared by every analytical page.

    The chosen values are mirrored into non-widget state so they survive a page
    switch: Streamlit drops widget state for widgets a run did not draw, and a
    filter that silently resets to 30 days when you change page is the fastest
    way to misread a dashboard.
    """
    state = st.session_state
    state.setdefault("gia_days_value", 30)
    state.setdefault("gia_channel_value", _ALL_CHANNELS)

    st.sidebar.markdown(components.sidebar_label("Période"), unsafe_allow_html=True)
    picked_days = st.sidebar.segmented_control(
        "Période (jours)",
        options=_PERIOD_OPTIONS,
        default=state["gia_days_value"],
        format_func=lambda value: f"{value} j",
        key="gia_days",
        label_visibility="collapsed",
    )
    days = picked_days if picked_days is not None else state["gia_days_value"]
    state["gia_days_value"] = days

    st.sidebar.markdown(components.sidebar_label("Canal"), unsafe_allow_html=True)
    options = [_ALL_CHANNELS, *[c.value for c in Channel]]
    stored = state["gia_channel_value"]
    picked_channel = st.sidebar.selectbox(
        "Canal",
        options=options,
        index=options.index(stored) if stored in options else 0,
        format_func=channel_label,
        key="gia_channel",
        label_visibility="collapsed",
    )
    state["gia_channel_value"] = picked_channel
    channel = None if picked_channel == _ALL_CHANNELS else picked_channel

    st.sidebar.caption(
        f"{days} jours glissants, comparés aux {days} précédents. "
        "Le filtre suit la navigation."
    )
    return days, channel


def chart(altair_chart, *, key: str | None = None) -> None:
    """Render a chart with our own Vega config.

    `theme=None` on purpose: the builders in `dashboard.charts` already set
    axes, typography and palette, and Streamlit's default theme would repaint
    the series colours that were validated for these surfaces.
    """
    st.altair_chart(altair_chart, width="stretch", theme=None, key=key)


def table_twin(label: str, frame, *, column_config: dict | None = None) -> None:
    """The accessible equivalent of the chart above it, folded away by default.

    Three of the light-mode series colours sit below 3:1 against the surface.
    The palette allows that only when the values are reachable another way, so
    every chart on these pages ships one of these.
    """
    with st.expander(label):
        st.dataframe(
            frame,
            width="stretch",
            hide_index=True,
            column_config=column_config or {},
        )


def render_claims(claims: Sequence[object], *, empty: str = "Aucune assertion produite.") -> None:
    """Evidence claims as cards, keeping the FACT / INTERPRETATION split visible."""
    if not claims:
        st.caption(empty)
        return
    for claim in claims:
        label = getattr(getattr(claim, "label", ""), "value", str(getattr(claim, "label", "")))
        st.markdown(
            components.claim_card(
                label,
                getattr(claim, "text", ""),
                source_tool=getattr(claim, "source_tool", None),
                numbers=getattr(claim, "numbers", None) or {},
            ),
            unsafe_allow_html=True,
        )
