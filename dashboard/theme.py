"""Design tokens and the stylesheet that carries them — pure, no Streamlit runtime.

Two palettes live here and they are deliberately kept apart:

* **Brand chrome** — the deep green and the gold. It identifies the *product*:
  hero, sidebar, buttons, focus rings, badges.
* **Data palette** — the categorical order, the brand-green ordinal ramp and the
  fixed status colours. It identifies *the data*.

Letting the brand accent double as a series colour would make one hue mean two
things at once, so the brand green never encodes a value and no series colour is
ever used for chrome.

Both palettes were checked with the data-viz validator against the two surfaces
below rather than by eye:

* categorical, light on ``#fcfcfb`` — worst adjacent CVD ΔE 9.1, normal-vision
  ΔE 19.6; aqua / yellow / magenta land under 3:1, so every chart using them
  carries direct labels or a table twin;
* categorical, dark on ``#141c19`` — worst adjacent CVD ΔE 8.4, all slots ≥ 3:1;
* funnel ramp, both modes — one hue, monotone lightness, ΔL ≥ 0.06 between
  steps, light end ≥ 2:1 against its own surface.

Keep this file in step with ``.streamlit/config.toml``: that file colours the
widgets Streamlit paints itself, this one colours everything we draw.
"""

from __future__ import annotations

from dataclasses import dataclass
from string import Template

LIGHT = "light"
DARK = "dark"


@dataclass(frozen=True)
class Tokens:
    """One resolved theme. Field names are the CSS custom-property names."""

    name: str

    # Planes and surfaces
    plane: str
    surface: str
    surface_alt: str
    surface_sunken: str

    # Ink
    ink: str
    ink_soft: str
    ink_muted: str

    # Hairlines
    grid: str
    axis: str
    border: str
    shadow: str
    shadow_lift: str

    # Brand chrome
    brand_deep: str
    brand: str
    brand_bright: str
    gold: str
    on_brand: str

    # Data palette
    categorical: tuple[str, ...]
    funnel_ramp: tuple[str, ...]
    series: str
    series_muted: str

    # Status (fixed across modes — an icon and a label always ride along)
    good: str
    warning: str
    serious: str
    critical: str
    good_text: str

    @property
    def is_dark(self) -> bool:
        return self.name == DARK


#: Status steps are mode-invariant on purpose: a colour that means "critical"
#: must not shift meaning when the reader flips the theme.
_GOOD = "#0ca30c"
_WARNING = "#fab219"
_SERIOUS = "#ec835a"
_CRITICAL = "#d03b3b"


LIGHT_TOKENS = Tokens(
    name=LIGHT,
    plane="#f7f8f6",
    surface="#fcfcfb",
    surface_alt="#f0f2ef",
    surface_sunken="#e9ece8",
    ink="#0b0b0b",
    ink_soft="#52514e",
    ink_muted="#898781",
    grid="#e1e0d9",
    axis="#c3c2b7",
    border="rgba(11,11,11,0.10)",
    shadow="0 1px 2px rgba(11,32,26,0.05), 0 6px 18px -12px rgba(11,32,26,0.22)",
    shadow_lift="0 2px 4px rgba(11,32,26,0.06), 0 18px 36px -20px rgba(11,32,26,0.34)",
    brand_deep="#0f2a24",
    brand="#1c4a3e",
    brand_bright="#1e8a63",
    gold="#c4a574",
    on_brand="#f2f7f4",
    categorical=(
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#e87ba4",
        "#008300",
        "#4a3aa7",
        "#e34948",
    ),
    funnel_ramp=("#6fc09f", "#3ea77f", "#1e8a63", "#14684a", "#0f4634"),
    series="#2a78d6",
    series_muted="#c8ccc7",
    good=_GOOD,
    warning=_WARNING,
    serious=_SERIOUS,
    critical=_CRITICAL,
    good_text="#006300",
)


DARK_TOKENS = Tokens(
    name=DARK,
    plane="#0b100e",
    surface="#141c19",
    surface_alt="#1b2421",
    surface_sunken="#101815",
    ink="#f2f5f3",
    ink_soft="#c3c2b7",
    ink_muted="#8d968f",
    grid="#242d29",
    axis="#33403b",
    border="rgba(255,255,255,0.10)",
    shadow="0 1px 2px rgba(0,0,0,0.45), 0 6px 18px -12px rgba(0,0,0,0.7)",
    shadow_lift="0 2px 4px rgba(0,0,0,0.5), 0 18px 36px -20px rgba(0,0,0,0.85)",
    brand_deep="#0a120f",
    brand="#173d33",
    brand_bright="#4fae86",
    gold="#d8bd92",
    on_brand="#eaf2ee",
    categorical=(
        "#3987e5",
        "#d95926",
        "#199e70",
        "#c98500",
        "#d55181",
        "#008300",
        "#9085e9",
        "#e66767",
    ),
    funnel_ramp=("#a8dcc4", "#79c8a5", "#4fae86", "#2f8b68", "#1f6a4f"),
    series="#3987e5",
    series_muted="#3c4844",
    good=_GOOD,
    warning=_WARNING,
    serious=_SERIOUS,
    critical=_CRITICAL,
    good_text=_GOOD,
)


def tokens_for(name: str | None) -> Tokens:
    """Resolve a theme name. Anything unrecognised falls back to light."""
    return DARK_TOKENS if (name or "").lower() == DARK else LIGHT_TOKENS


_STYLESHEET = Template(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --gia-plane: $plane;
  --gia-surface: $surface;
  --gia-surface-alt: $surface_alt;
  --gia-surface-sunken: $surface_sunken;
  --gia-ink: $ink;
  --gia-ink-soft: $ink_soft;
  --gia-ink-muted: $ink_muted;
  --gia-grid: $grid;
  --gia-axis: $axis;
  --gia-border: $border;
  --gia-shadow: $shadow;
  --gia-shadow-lift: $shadow_lift;
  --gia-brand-deep: $brand_deep;
  --gia-brand: $brand;
  --gia-brand-bright: $brand_bright;
  --gia-gold: $gold;
  --gia-on-brand: $on_brand;
  --gia-series: $series;
  --gia-good: $good;
  --gia-warning: $warning;
  --gia-serious: $serious;
  --gia-critical: $critical;
  --gia-ease: cubic-bezier(.22,.61,.36,1);
}

/* ---------------------------------------------------------------- motion */
/* Streamlit repaints the whole page on every interaction, so entrances are
   kept short: long enough to give the eye an order to follow, short enough
   that a filter change does not feel like a page load. */

@keyframes gia-rise {
  from { opacity: 0; transform: translateY(9px); }
  to   { opacity: 1; transform: none; }
}
@keyframes gia-fade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes gia-grow {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}
@keyframes gia-drift {
  0%,100% { transform: translate3d(0,0,0) scale(1); }
  50%     { transform: translate3d(-4%,3%,0) scale(1.12); }
}
@keyframes gia-breathe {
  0%,100% { opacity: 1; }
  50%     { opacity: .35; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 1ms !important;
  }
}

/* ------------------------------------------------------------- app shell */

html, body, [class*="css"] {
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.stMain { background: var(--gia-plane); }

/* Streamlit reserves a slot for every element, including one that only carries
   a <style> tag. Left alone it prints as a blank gap at the top of the page. */
[data-testid="stElementContainer"]:has(> .stMarkdown style),
[data-testid="stElementContainer"]:has(> .stHtml style) { display: none !important; }

[data-testid="stHeader"] { background: transparent; }

.stMain [data-testid="stVerticalBlockBorderWrapper"],
.stMain [data-testid="stMetric"],
.stMain [data-testid="stDataFrame"],
.stMain [data-testid="stVegaLiteChart"],
.stMain [data-testid="stAlertContainer"],
.gia-rise {
  animation: gia-rise .38s var(--gia-ease) both;
}

.stMain [data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] { animation-delay: 0ms; }
.stMain [data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { animation-delay: 55ms; }
.stMain [data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { animation-delay: 110ms; }
.stMain [data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { animation-delay: 165ms; }
.stMain [data-testid="stHorizontalBlock"] > div:nth-child(5) [data-testid="stMetric"] { animation-delay: 220ms; }

/* ------------------------------------------------------------------ hero */

.gia-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  border-radius: 18px;
  padding: 1.5rem 1.7rem 1.6rem;
  margin: .2rem 0 1.15rem;
  color: var(--gia-on-brand);
  background:
    radial-gradient(120% 160% at 88% -30%, rgba(196,165,116,.42) 0%, rgba(196,165,116,0) 58%),
    linear-gradient(122deg, $brand_deep 0%, $brand 58%, $brand_deep 100%);
  box-shadow: var(--gia-shadow-lift);
  animation: gia-rise .45s var(--gia-ease) both;
}
.gia-hero::before {
  content: "";
  position: absolute;
  inset: -35% -10% auto auto;
  width: 30rem; height: 30rem;
  background: radial-gradient(circle, rgba(120,220,180,.30) 0%, rgba(120,220,180,0) 62%);
  z-index: -1;
  animation: gia-drift 22s ease-in-out infinite;
}
.gia-hero__brand {
  display: inline-flex; align-items: center; gap: .5rem;
  font-size: .715rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase;
  color: var(--gia-gold);
}
.gia-hero__brand::before {
  content: "";
  width: .5rem; height: .5rem; border-radius: 2px;
  background: var(--gia-gold);
  transform: rotate(45deg);
}
.gia-hero__title {
  font-size: 1.95rem; font-weight: 700; line-height: 1.12;
  letter-spacing: -.022em;
  margin: .5rem 0 .35rem;
}
.gia-hero__sub {
  margin: 0; max-width: 46rem;
  font-size: .95rem; line-height: 1.5;
  color: rgba(242,247,244,.78);
}
.gia-hero__meta {
  display: flex; flex-wrap: wrap; gap: .45rem;
  margin-top: 1rem;
}
.gia-hero__chip {
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .3rem .65rem;
  border-radius: 999px;
  font-size: .775rem; font-weight: 500;
  color: rgba(242,247,244,.9);
  background: rgba(255,255,255,.09);
  border: 1px solid rgba(255,255,255,.14);
  backdrop-filter: blur(4px);
  animation: gia-fade .5s var(--gia-ease) both;
}
.gia-hero__chip--live::before {
  content: "";
  width: .45rem; height: .45rem; border-radius: 50%;
  background: #6fe0ac;
  animation: gia-breathe 2.4s ease-in-out infinite;
}

/* --------------------------------------------------------------- sidebar */

[data-testid="stSidebar"] {
  background:
    radial-gradient(100% 60% at 50% 0%, rgba(196,165,116,.13) 0%, rgba(196,165,116,0) 70%),
    linear-gradient(180deg, $brand_deep 0%, $brand_deep 62%, $brand 100%);
}
[data-testid="stSidebar"] * { color: var(--gia-on-brand); }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: rgba(230,239,234,.62) !important; }

.gia-side-brand {
  display: flex; align-items: center; gap: .6rem;
  padding: .15rem 0 .9rem;
  margin-bottom: .35rem;
  border-bottom: 1px solid rgba(255,255,255,.10);
}
.gia-side-brand__mark {
  display: grid; place-items: center;
  width: 2rem; height: 2rem; border-radius: 9px;
  background: linear-gradient(135deg, var(--gia-gold) 0%, #8f7345 100%);
  color: $brand_deep; font-weight: 700; font-size: .95rem;
  box-shadow: 0 4px 12px -6px rgba(196,165,116,.9);
}
.gia-side-brand__name {
  font-size: .84rem; font-weight: 650; letter-spacing: -.01em; line-height: 1.15;
}
.gia-side-brand__tag {
  font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;
  color: rgba(230,239,234,.5);
}
.gia-side-label {
  font-size: .68rem; font-weight: 600;
  letter-spacing: .13em; text-transform: uppercase;
  color: rgba(230,239,234,.5);
  margin: 1.05rem 0 .3rem;
}

[data-testid="stSidebarNav"] a { border-radius: 8px; transition: background .16s var(--gia-ease); }
[data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.07); }

/* --------------------------------------------------------------- metrics */

.stMain [data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
  background: var(--gia-surface);
  border: 1px solid var(--gia-border);
  border-radius: 14px;
  padding: .95rem 1.05rem 1rem;
  box-shadow: var(--gia-shadow);
  transition: transform .22s var(--gia-ease), box-shadow .22s var(--gia-ease);
}
.stMain [data-testid="stMetric"]::after {
  content: "";
  position: absolute; inset: 0 auto 0 0;
  width: 3px;
  background: linear-gradient(180deg, var(--gia-brand-bright), var(--gia-gold));
  opacity: 0; transition: opacity .22s var(--gia-ease);
}
.stMain [data-testid="stMetric"]:hover {
  transform: translateY(-2px);
  box-shadow: var(--gia-shadow-lift);
}
.stMain [data-testid="stMetric"]:hover::after { opacity: 1; }
[data-testid="stMetricLabel"] p {
  font-size: .78rem !important; font-weight: 550;
  letter-spacing: .01em;
  color: var(--gia-ink-soft) !important;
}
[data-testid="stMetricValue"] { letter-spacing: -.028em; }
[data-testid="stMetricDelta"] { font-size: .8rem; font-weight: 550; }

/* ----------------------------------------------------------------- cards */

.gia-card {
  background: var(--gia-surface);
  border: 1px solid var(--gia-border);
  border-radius: 14px;
  padding: 1rem 1.15rem;
  box-shadow: var(--gia-shadow);
  animation: gia-rise .38s var(--gia-ease) both;
}

.gia-banner {
  display: flex; align-items: flex-start; gap: .7rem;
  border-radius: 12px;
  padding: .7rem .95rem;
  margin-bottom: .9rem;
  font-size: .875rem; line-height: 1.45;
  color: var(--gia-ink-soft);
  background: var(--gia-surface-alt);
  border: 1px solid var(--gia-border);
  border-left: 3px solid var(--gia-gold);
  animation: gia-rise .38s var(--gia-ease) both;
}
.gia-banner--live { border-left-color: var(--gia-brand-bright); }
.gia-banner strong { color: var(--gia-ink); font-weight: 600; }
.gia-banner__icon { flex: none; font-size: 1rem; line-height: 1.35; }

.gia-section {
  display: flex; align-items: baseline; gap: .6rem;
  margin: 1.6rem 0 .2rem;
}
.gia-section__idx {
  font-size: .72rem; font-weight: 650; letter-spacing: .12em;
  color: var(--gia-gold);
  font-variant-numeric: tabular-nums;
}
.gia-section__title {
  font-size: 1.12rem; font-weight: 650; letter-spacing: -.012em;
  color: var(--gia-ink);
}
.gia-section__note {
  margin: .2rem 0 .75rem;
  font-size: .85rem; line-height: 1.5;
  color: var(--gia-ink-muted);
  max-width: 52rem;
}

/* --------------------------------------------------------------- badges */

.gia-badge {
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .16rem .5rem;
  border-radius: 6px;
  font-size: .68rem; font-weight: 650;
  letter-spacing: .07em; text-transform: uppercase;
  white-space: nowrap;
  border: 1px solid transparent;
}
.gia-badge--fact {
  color: $series; background: color-mix(in srgb, $series 14%, transparent);
  border-color: color-mix(in srgb, $series 32%, transparent);
}
.gia-badge--interpretation {
  color: $gold; background: color-mix(in srgb, $gold 16%, transparent);
  border-color: color-mix(in srgb, $gold 38%, transparent);
}
.gia-badge--recommendation {
  color: var(--gia-brand-bright); background: color-mix(in srgb, var(--gia-brand-bright) 14%, transparent);
  border-color: color-mix(in srgb, var(--gia-brand-bright) 34%, transparent);
}
.gia-badge--neutral {
  color: var(--gia-ink-muted); background: var(--gia-surface-alt);
  border-color: var(--gia-border);
}
.gia-badge--good     { color: var(--gia-good);     background: color-mix(in srgb, var(--gia-good) 13%, transparent);     border-color: color-mix(in srgb, var(--gia-good) 32%, transparent); }
.gia-badge--warning  { color: var(--gia-ink);      background: color-mix(in srgb, var(--gia-warning) 22%, transparent);  border-color: color-mix(in srgb, var(--gia-warning) 46%, transparent); }
.gia-badge--serious  { color: var(--gia-ink);      background: color-mix(in srgb, var(--gia-serious) 22%, transparent);  border-color: color-mix(in srgb, var(--gia-serious) 46%, transparent); }
.gia-badge--critical { color: var(--gia-critical); background: color-mix(in srgb, var(--gia-critical) 13%, transparent); border-color: color-mix(in srgb, var(--gia-critical) 34%, transparent); }

/* ---------------------------------------------------------------- claims */

.gia-claim {
  position: relative;
  background: var(--gia-surface);
  border: 1px solid var(--gia-border);
  border-radius: 12px;
  padding: .8rem .95rem .85rem;
  margin-bottom: .55rem;
  box-shadow: var(--gia-shadow);
  animation: gia-rise .36s var(--gia-ease) both;
  transition: transform .2s var(--gia-ease), box-shadow .2s var(--gia-ease);
}
.gia-claim:hover { transform: translateY(-1px); box-shadow: var(--gia-shadow-lift); }
.gia-claim__head { display: flex; align-items: center; gap: .5rem; margin-bottom: .4rem; }
.gia-claim__text {
  margin: 0;
  font-size: .93rem; line-height: 1.55;
  color: var(--gia-ink);
}
.gia-claim__src {
  display: inline-block; margin-top: .45rem;
  font-size: .74rem; color: var(--gia-ink-muted);
}
.gia-claim__src code {
  font-size: .72rem;
  padding: .05rem .3rem; border-radius: 4px;
  background: var(--gia-surface-alt); color: var(--gia-ink-soft);
}
.gia-claim__nums {
  display: flex; flex-wrap: wrap; gap: .35rem;
  margin-top: .5rem;
}
.gia-claim__num {
  font-size: .75rem;
  font-variant-numeric: tabular-nums;
  padding: .16rem .45rem; border-radius: 6px;
  background: var(--gia-surface-alt); color: var(--gia-ink-soft);
  border: 1px solid var(--gia-border);
}
.gia-claim__num b { color: var(--gia-ink); font-weight: 600; }

/* ----------------------------------------------------------------- meter */

.gia-meter { display: flex; align-items: center; gap: .6rem; }
.gia-meter__track {
  flex: 1;
  height: .5rem; border-radius: 999px;
  background: var(--gia-surface-sunken);
  overflow: hidden;
}
.gia-meter__fill {
  height: 100%; border-radius: 999px;
  width: var(--gia-w, 0%);
  background: var(--gia-c, var(--gia-brand-bright));
  transform-origin: left center;
  animation: gia-grow .7s var(--gia-ease) both;
}
.gia-meter__value {
  flex: none; min-width: 3.4rem; text-align: right;
  font-size: .8rem; font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--gia-ink-soft);
}

/* ------------------------------------------------------------- controls */

.stMain .stButton > button,
.stMain [data-testid="stFormSubmitButton"] > button {
  font-weight: 550;
  transition: transform .16s var(--gia-ease), box-shadow .16s var(--gia-ease),
              background-color .16s var(--gia-ease);
}
.stMain .stButton > button:hover { transform: translateY(-1px); box-shadow: var(--gia-shadow); }
.stMain .stButton > button:active { transform: translateY(0); }

[data-baseweb="tab-list"] { gap: .25rem; }
[data-baseweb="tab"] { transition: color .16s var(--gia-ease); }

[data-testid="stExpander"] details {
  border-radius: 12px;
  border: 1px solid var(--gia-border);
  background: var(--gia-surface);
  overflow: hidden;
}
[data-testid="stExpander"] summary { transition: background .16s var(--gia-ease); }
[data-testid="stExpander"] summary:hover { background: var(--gia-surface-alt); }

.stMain [data-testid="stVegaLiteChart"] {
  background: var(--gia-surface);
  border: 1px solid var(--gia-border);
  border-radius: 14px;
  padding: .9rem .7rem .5rem;
  box-shadow: var(--gia-shadow);
}

.stMain [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Streamlit's own spinner, restyled so a running agent reads as work in
   progress rather than as an error state. */
[data-testid="stSpinner"] { color: var(--gia-ink-muted); font-size: .87rem; }
</style>
"""
)


def stylesheet(tokens: Tokens) -> str:
    """The full ``<style>`` block for one theme.

    Pure string work so it can be asserted on in tests: the page module only
    has to hand the result to ``st.markdown``.
    """
    return _STYLESHEET.substitute(
        plane=tokens.plane,
        surface=tokens.surface,
        surface_alt=tokens.surface_alt,
        surface_sunken=tokens.surface_sunken,
        ink=tokens.ink,
        ink_soft=tokens.ink_soft,
        ink_muted=tokens.ink_muted,
        grid=tokens.grid,
        axis=tokens.axis,
        border=tokens.border,
        shadow=tokens.shadow,
        shadow_lift=tokens.shadow_lift,
        brand_deep=tokens.brand_deep,
        brand=tokens.brand,
        brand_bright=tokens.brand_bright,
        gold=tokens.gold,
        on_brand=tokens.on_brand,
        series=tokens.series,
        good=tokens.good,
        warning=tokens.warning,
        serious=tokens.serious,
        critical=tokens.critical,
    )
