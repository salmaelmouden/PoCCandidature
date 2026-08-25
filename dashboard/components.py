"""HTML fragments for the dashboard — pure functions, no Streamlit runtime.

Streamlit has no primitive for a badge, a claim card or a meter, so these are
built as markup and handed to ``st.markdown(..., unsafe_allow_html=True)``.
Keeping them here rather than inline in the pages means two things: a page reads
as layout instead of as a wall of strings, and the markup can be asserted on in
tests — including the part that actually matters, which is that every value
reaching the page is escaped before it becomes HTML.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from html import escape

from dashboard.formatting import CLAIM_FR, fmt_int, fmt_pct, fr

#: Semantic label → badge modifier. The analyst's FACT / INTERPRETATION split is
#: the whole point of its report format, so it gets a visual weight of its own.
_CLAIM_KIND = {
    "FACT": "fact",
    "INTERPRETATION": "interpretation",
    "RECOMMENDATION": "recommendation",
}

_BADGE_KINDS = frozenset(
    {"fact", "interpretation", "recommendation", "neutral", "good", "warning", "serious", "critical"}
)


def badge(text: str, kind: str = "neutral") -> str:
    """A small pill. Unknown kinds degrade to neutral rather than losing style."""
    modifier = kind if kind in _BADGE_KINDS else "neutral"
    return f'<span class="gia-badge gia-badge--{modifier}">{escape(text)}</span>'


def hero(
    title: str,
    subtitle: str,
    *,
    brand: str = "Growth Intelligence AI",
    chips: Sequence[tuple[str, bool]] = (),
) -> str:
    """Page banner. ``chips`` are ``(label, is_live)`` pairs shown under the text."""
    chip_html = "".join(
        f'<span class="gia-hero__chip{" gia-hero__chip--live" if live else ""}"'
        f' style="animation-delay:{60 + index * 60}ms">{escape(label)}</span>'
        for index, (label, live) in enumerate(chips)
    )
    meta = f'<div class="gia-hero__meta">{chip_html}</div>' if chip_html else ""
    return (
        '<div class="gia-hero">'
        f'<span class="gia-hero__brand">{escape(brand)}</span>'
        f'<h1 class="gia-hero__title">{escape(title)}</h1>'
        f'<p class="gia-hero__sub">{escape(subtitle)}</p>'
        f"{meta}"
        "</div>"
    )


def sidebar_brand(name: str = "Growth Intelligence AI", tagline: str = "Analyse growth") -> str:
    return (
        '<div class="gia-side-brand">'
        '<span class="gia-side-brand__mark">◈</span>'
        "<span>"
        f'<span class="gia-side-brand__name">{escape(name)}</span><br>'
        f'<span class="gia-side-brand__tag">{escape(tagline)}</span>'
        "</span>"
        "</div>"
    )


def sidebar_label(text: str) -> str:
    return f'<div class="gia-side-label">{escape(text)}</div>'


def banner(message_html: str, *, icon: str = "◆", live: bool = False) -> str:
    """Provenance / context strip.

    ``message_html`` is trusted markup assembled by the caller from already
    escaped pieces — it is the one place where the caller needs ``<strong>``.
    """
    modifier = " gia-banner--live" if live else ""
    return (
        f'<div class="gia-banner{modifier}">'
        f'<span class="gia-banner__icon">{escape(icon)}</span>'
        f"<span>{message_html}</span>"
        "</div>"
    )


def section(title: str, *, index: str | None = None, note: str | None = None) -> str:
    """Section heading with an optional ordinal and an optional standfirst."""
    idx = f'<span class="gia-section__idx">{escape(index)}</span>' if index else ""
    body = f'<p class="gia-section__note">{escape(note)}</p>' if note else ""
    return (
        f'<div class="gia-section">{idx}'
        f'<span class="gia-section__title">{escape(title)}</span></div>{body}'
    )


def meter(ratio: float, *, color: str, label: str | None = None) -> str:
    """A single ratio against its track. ``ratio`` is clamped into 0–1."""
    share = max(0.0, min(1.0, float(ratio)))
    value = f'<span class="gia-meter__value">{escape(label)}</span>' if label else ""
    return (
        '<div class="gia-meter"><div class="gia-meter__track">'
        f'<div class="gia-meter__fill" style="--gia-w:{share * 100:.2f}%;'
        f'--gia-c:{escape(color)}"></div></div>'
        f"{value}</div>"
    )


def _number_chip(key: str, value: float | str | None) -> str:
    if value is None:
        shown = "—"
    elif isinstance(value, bool):
        shown = "oui" if value else "non"
    elif isinstance(value, int):
        shown = fmt_int(value)
    elif isinstance(value, float):
        # Anything inside the unit interval is a rate in this codebase; showing
        # it as "0,03" instead of "3,1 %" is how a reader misreads a funnel.
        shown = fmt_pct(value) if 0.0 <= value <= 1.0 else fr(value)
    else:
        shown = str(value)
    return f'<span class="gia-claim__num">{escape(key)} <b>{escape(shown)}</b></span>'


def claim_card(
    label: str,
    text: str,
    *,
    source_tool: str | None = None,
    numbers: Mapping[str, float | int | str | None] | None = None,
) -> str:
    """One evidence claim, with its semantic label carried visually."""
    kind = _CLAIM_KIND.get(label.upper(), "neutral")
    head = badge(CLAIM_FR.get(label.upper(), label), kind)
    source = (
        f'<span class="gia-claim__src">source&nbsp;: <code>{escape(source_tool)}</code></span>'
        if source_tool
        else ""
    )
    chips = "".join(_number_chip(key, value) for key, value in (numbers or {}).items())
    chip_row = f'<div class="gia-claim__nums">{chips}</div>' if chips else ""
    return (
        '<div class="gia-claim">'
        f'<div class="gia-claim__head">{head}</div>'
        f'<p class="gia-claim__text">{escape(text)}</p>'
        f"{chip_row}{source}"
        "</div>"
    )


def insight_card(
    title: str,
    value: str,
    *,
    note: str | None = None,
    badge_text: str | None = None,
    badge_kind: str = "neutral",
    meter_ratio: float | None = None,
    meter_color: str | None = None,
    meter_label: str | None = None,
) -> str:
    """A single called-out reading: a headline number with its context.

    The form the data-viz guidance calls a stat tile — used where a one-bar
    chart would otherwise appear, which is most places a dashboard is tempted
    to draw one.
    """
    tag = (
        f'<div style="margin-bottom:.55rem">{badge(badge_text, badge_kind)}</div>'
        if badge_text
        else ""
    )
    body = f'<p class="gia-section__note" style="margin:.45rem 0 0">{escape(note)}</p>' if note else ""
    bar = (
        meter(meter_ratio, color=meter_color or "#1e8a63", label=meter_label)
        if meter_ratio is not None
        else ""
    )
    gap = '<div style="margin-top:.7rem"></div>' if bar else ""
    return (
        '<div class="gia-card">'
        f"{tag}"
        f'<div style="font-size:.78rem;font-weight:550;color:var(--gia-ink-soft)">{escape(title)}</div>'
        f'<div style="font-size:1.55rem;font-weight:650;letter-spacing:-.025em;'
        f'color:var(--gia-ink);margin-top:.2rem">{escape(value)}</div>'
        f"{body}{gap}{bar}"
        "</div>"
    )


def rewrite_card(
    *,
    original: str,
    proposal: str,
    meta: str,
    register: str,
    url: str,
) -> str:
    """Before/after for one title.

    Built as markup rather than passed to ``st.markdown`` as text for one
    reason: these strings are video titles straight out of the catalogue, full
    of ``|``, ``*``, ``#`` and emoji. Rendered as markdown they would silently
    reformat — the ``#`` in "Finary Talk #20" is one paste away from becoming a
    heading — and a page arguing about titles cannot afford to misquote one.
    """
    return (
        '<div class="gia-card">'
        f'<div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-bottom:.6rem">'
        f"{badge(register, 'recommendation')}"
        f'<span style="font-size:.74rem;color:var(--gia-ink-soft)">{escape(meta)}</span>'
        "</div>"
        f'<div style="font-size:.72rem;font-weight:600;letter-spacing:.04em;'
        f'text-transform:uppercase;color:var(--gia-ink-soft)">Actuel</div>'
        f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" '
        f'style="display:block;font-size:.95rem;color:var(--gia-ink-soft);'
        f'text-decoration:none;margin:.15rem 0 .8rem">{escape(original)}</a>'
        f'<div style="font-size:.72rem;font-weight:600;letter-spacing:.04em;'
        f'text-transform:uppercase;color:var(--gia-ink-soft)">Proposé</div>'
        f'<div style="font-size:1.05rem;font-weight:600;letter-spacing:-.015em;'
        f'color:var(--gia-ink);margin-top:.15rem">{escape(proposal)}</div>'
        "</div>"
    )


def provenance_message(*, has_synthetic: bool, labels: Iterable[str]) -> str:
    """The sentence under the hero that says where the numbers come from."""
    names = sorted(labels)
    label_text = escape(", ".join(names)) if names else "inconnu"
    if has_synthetic:
        return (
            "Ces métriques incluent des <strong>données synthétiques étiquetées</strong> "
            f"({label_text}). Ce ne sont pas des données réelles d'entreprise."
        )
    return f"Étiquettes présentes dans cette vue&nbsp;: <strong>{label_text}</strong>."
