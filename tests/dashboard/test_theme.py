"""Tests for the design tokens and the stylesheet they produce."""

from __future__ import annotations

import re

import pytest

from dashboard.theme import DARK, DARK_TOKENS, LIGHT, LIGHT_TOKENS, stylesheet, tokens_for


def test_tokens_resolve_by_name() -> None:
    assert tokens_for(LIGHT) is LIGHT_TOKENS
    assert tokens_for(DARK) is DARK_TOKENS
    assert tokens_for("DARK") is DARK_TOKENS


@pytest.mark.parametrize("name", [None, "", "sepia", "auto"])
def test_unknown_theme_falls_back_to_light(name: str | None) -> None:
    """`st.context.theme.type` is not guaranteed — an unknown value must still render."""
    assert tokens_for(name) is LIGHT_TOKENS


def test_is_dark_flag() -> None:
    assert DARK_TOKENS.is_dark is True
    assert LIGHT_TOKENS.is_dark is False


@pytest.mark.parametrize("tokens", [LIGHT_TOKENS, DARK_TOKENS])
def test_stylesheet_substitutes_every_placeholder(tokens) -> None:
    """`Template.substitute` raises on a missing key, so building it is the check.

    The regex guards the other direction: a `$word` that survived into the
    output would mean a placeholder was written but never declared.
    """
    css = stylesheet(tokens)

    assert css.startswith("\n<style>")
    assert css.rstrip().endswith("</style>")
    assert not re.search(r"\$[A-Za-z_]", css)


@pytest.mark.parametrize("tokens", [LIGHT_TOKENS, DARK_TOKENS])
def test_stylesheet_carries_its_own_surfaces(tokens) -> None:
    css = stylesheet(tokens)

    assert f"--gia-surface: {tokens.surface};" in css
    assert f"--gia-plane: {tokens.plane};" in css
    assert f"--gia-ink: {tokens.ink};" in css


def test_the_two_modes_are_actually_different() -> None:
    """Guards against a copy-paste that leaves dark mode painted for light."""
    assert stylesheet(LIGHT_TOKENS) != stylesheet(DARK_TOKENS)
    assert LIGHT_TOKENS.surface != DARK_TOKENS.surface
    assert LIGHT_TOKENS.categorical != DARK_TOKENS.categorical
    assert LIGHT_TOKENS.funnel_ramp != DARK_TOKENS.funnel_ramp


def test_motion_is_opt_out() -> None:
    """Entrance animation is decoration; a reader who asked for less must get less."""
    for tokens in (LIGHT_TOKENS, DARK_TOKENS):
        assert "@media (prefers-reduced-motion: reduce)" in stylesheet(tokens)


@pytest.mark.parametrize("tokens", [LIGHT_TOKENS, DARK_TOKENS])
def test_palette_shapes(tokens) -> None:
    """Eight categorical slots, five funnel steps — the counts the charts assume."""
    assert len(tokens.categorical) == 8
    assert len(tokens.funnel_ramp) == 5
    assert all(re.fullmatch(r"#[0-9a-f]{6}", hex_) for hex_ in tokens.categorical)
    assert all(re.fullmatch(r"#[0-9a-f]{6}", hex_) for hex_ in tokens.funnel_ramp)


def test_status_colours_do_not_change_between_modes() -> None:
    """A colour that means "critical" must not shift meaning with the theme."""
    assert LIGHT_TOKENS.critical == DARK_TOKENS.critical
    assert LIGHT_TOKENS.warning == DARK_TOKENS.warning
    assert LIGHT_TOKENS.serious == DARK_TOKENS.serious
    assert LIGHT_TOKENS.good == DARK_TOKENS.good


def test_status_colours_are_not_series_colours() -> None:
    """Otherwise a status cue could be mistaken for the fourth series."""
    for tokens in (LIGHT_TOKENS, DARK_TOKENS):
        status = {tokens.good, tokens.warning, tokens.serious, tokens.critical}
        assert status.isdisjoint(set(tokens.categorical))
