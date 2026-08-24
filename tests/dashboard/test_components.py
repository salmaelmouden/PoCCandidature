"""Tests for the HTML fragments the dashboard injects.

These run with `unsafe_allow_html=True`, so escaping is not a nicety here: a
content title or a tool name that reaches the page unescaped is markup
injection. Every test that pushes a tag through a component is checking that.
"""

from __future__ import annotations

import pytest

from dashboard.components import (
    badge,
    banner,
    claim_card,
    hero,
    insight_card,
    meter,
    provenance_message,
    section,
    sidebar_brand,
    sidebar_label,
)

INJECTION = '<script>alert("x")</script>'


def test_badge_kinds_are_a_closed_set() -> None:
    assert 'gia-badge--fact' in badge("Fait", "fact")
    assert 'gia-badge--critical' in badge("P0", "critical")
    # An unknown kind must degrade to a styled pill, never to an unstyled one.
    assert 'gia-badge--neutral' in badge("Autre", "chartreuse")


def test_badge_escapes_its_text() -> None:
    assert "<script>" not in badge(INJECTION)
    assert "&lt;script&gt;" in badge(INJECTION)


def test_hero_escapes_title_and_subtitle() -> None:
    markup = hero(INJECTION, INJECTION)

    assert "<script>" not in markup
    assert markup.count("&lt;script&gt;") == 2


def test_hero_chips_stagger_their_entrance() -> None:
    markup = hero("Titre", "Sous-titre", chips=[("30 jours", False), ("En direct", True)])

    assert "gia-hero__chip--live" in markup
    assert "animation-delay:60ms" in markup
    assert "animation-delay:120ms" in markup


def test_hero_without_chips_omits_the_meta_row() -> None:
    assert "gia-hero__meta" not in hero("Titre", "Sous-titre")


def test_section_index_and_note_are_optional() -> None:
    bare = section("Titre")
    full = section("Titre", index="01", note="Une note.")

    assert "gia-section__idx" not in bare
    assert "gia-section__note" not in bare
    assert "01" in full
    assert "Une note." in full


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [(-0.5, "0.00%"), (0.0, "0.00%"), (0.625, "62.50%"), (1.0, "100.00%"), (3.0, "100.00%")],
)
def test_meter_clamps_out_of_range_ratios(ratio: float, expected: str) -> None:
    """A rate above 1 is a data problem; a bar past its track is a rendering bug."""
    assert f"--gia-w:{expected}" in meter(ratio, color="#1e8a63")


def test_meter_label_is_optional_and_escaped() -> None:
    assert "gia-meter__value" not in meter(0.5, color="#1e8a63")
    assert "&lt;script&gt;" in meter(0.5, color="#1e8a63", label=INJECTION)


def test_claim_card_maps_the_semantic_label() -> None:
    fact = claim_card("FACT", "Les inscriptions ont baissé.")
    interpretation = claim_card("INTERPRETATION", "Probablement saisonnier.")

    assert "gia-badge--fact" in fact
    assert "Fait" in fact
    assert "gia-badge--interpretation" in interpretation
    assert "Interprétation" in interpretation


def test_claim_card_escapes_text_and_source() -> None:
    markup = claim_card("FACT", INJECTION, source_tool=INJECTION)

    assert "<script>" not in markup
    assert markup.count("&lt;script&gt;") == 2


def test_claim_card_renders_rates_as_percentages() -> None:
    """A rate shown as "0,03" is how a reader misreads a funnel by two orders."""
    markup = claim_card("FACT", "texte", numbers={"premium_rate": 0.031})

    assert "3,1" in markup
    assert "0,03" not in markup


def test_claim_card_number_chips_by_type() -> None:
    markup = claim_card(
        "FACT",
        "texte",
        numbers={"signups": 128402, "score": 4.25, "note": "n/a", "vide": None, "ok": True},
    )

    assert "128" in markup  # grouped integer
    assert "4,25" in markup  # float outside 0–1 keeps its decimals
    assert "n/a" in markup
    assert "—" in markup
    assert "oui" in markup


def test_claim_card_without_extras_stays_minimal() -> None:
    markup = claim_card("FACT", "texte")

    assert "gia-claim__nums" not in markup
    assert "gia-claim__src" not in markup


def test_insight_card_meter_is_opt_in() -> None:
    assert "gia-meter" not in insight_card("Titre", "42")
    assert "gia-meter" in insight_card("Titre", "42", meter_ratio=0.4, meter_color="#1e8a63")


def test_insight_card_escapes_its_value() -> None:
    assert "<script>" not in insight_card("Titre", INJECTION, note=INJECTION)


def test_provenance_names_synthetic_data_plainly() -> None:
    message = provenance_message(has_synthetic=True, labels=["synthetic_v1"])

    assert "synthétiques étiquetées" in message
    assert "synthetic_v1" in message
    assert "pas des données réelles" in message


def test_provenance_without_synthetic_just_lists_labels() -> None:
    message = provenance_message(has_synthetic=False, labels=["youtube_api"])

    assert "synthétiques" not in message
    assert "youtube_api" in message


def test_provenance_labels_are_sorted_and_escaped() -> None:
    message = provenance_message(has_synthetic=False, labels=["b_label", "a_label", INJECTION])

    assert message.index("a_label") < message.index("b_label")
    assert "<script>" not in message


def test_provenance_with_no_labels_says_so() -> None:
    assert "inconnu" in provenance_message(has_synthetic=False, labels=[])


def test_banner_keeps_caller_markup_but_escapes_the_icon() -> None:
    """The message is assembled from escaped pieces; the icon is raw input."""
    markup = banner("<strong>gras</strong>", icon=INJECTION)

    assert "<strong>gras</strong>" in markup
    assert "<script>" not in markup


def test_sidebar_fragments_escape_their_input() -> None:
    assert "<script>" not in sidebar_brand(INJECTION, INJECTION)
    assert "<script>" not in sidebar_label(INJECTION)
