"""French number, date and vocabulary formatting — pure, no Streamlit runtime.

The dashboard speaks French, and French typography is not a cosmetic detail
here: a thousands separator rendered as a comma reads as a decimal point to a
French reader, which silently changes the number. Everything that turns a value
into text goes through this module so the convention is applied once.
"""

from __future__ import annotations

from datetime import date

#: French typography puts a *narrow* no-break space inside numbers and a plain
#: no-break space before a unit sign, so neither can be wrapped onto a new line.
THIN_SPACE = " "
NBSP = " "

MONTHS_FR: tuple[str, ...] = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)

#: Funnel stage keys are English in the database (they are part of the data
#: contract); only the display label is translated.
STAGE_FR: dict[str, str] = {
    "views": "Vues",
    "visits": "Visites",
    "signups": "Inscriptions",
    "activated_users": "Utilisateurs activés",
    "premium_users": "Utilisateurs Premium",
}

STAGE_SHORT_FR: dict[str, str] = {
    "views": "Vues",
    "visits": "Visites",
    "signups": "Inscr.",
    "activated_users": "Activés",
    "premium_users": "Premium",
}

CHANNEL_FR: dict[str, str] = {
    "YouTube": "YouTube",
    "Organic Search": "Recherche organique",
    "LinkedIn": "LinkedIn",
    "Instagram": "Instagram",
    "Paid": "Payant",
    "Direct": "Direct",
}

TOPIC_SYNTH_FR: dict[str, str] = {
    "ETFs": "ETF",
    "Stocks": "Actions",
    "Crypto": "Crypto",
    "Personal Finance": "Finances personnelles",
    "Real Estate": "Immobilier",
    "Budgeting": "Budget",
}

ROUTE_FR: dict[str, str] = {
    "analyst_only": "analyste seul",
    "analyst_then_strategist": "analyste puis stratège",
    "experiment": "spécialiste expérimentation",
}

DECISION_FR: dict[str, str] = {
    "ship_treatment": "Déployer la variante",
    "keep_control": "Conserver le contrôle",
    "inconclusive": "Non concluant",
    "underpowered": "Puissance insuffisante",
}

CLAIM_FR: dict[str, str] = {
    "FACT": "Fait",
    "INTERPRETATION": "Interprétation",
    "RECOMMENDATION": "Recommandation",
}


def stage_label(stage: str) -> str:
    """Display label for a funnel stage, falling back to the raw key."""
    return STAGE_FR.get(stage, stage)


def stage_short(stage: str) -> str:
    return STAGE_SHORT_FR.get(stage, STAGE_FR.get(stage, stage))


def channel_label(channel: str | None) -> str:
    if channel is None:
        return "Tous les canaux"
    return CHANNEL_FR.get(channel, channel)


def topic_label(topic: str) -> str:
    return TOPIC_SYNTH_FR.get(topic, topic)


def transition_label(key: str) -> str:
    """``views->visits`` → ``Vues → Visites``, leaving unknown shapes alone."""
    for separator in ("->", "→", "_to_"):
        if separator in key:
            left, _, right = key.partition(separator)
            return f"{stage_short(left.strip())} → {stage_short(right.strip())}"
    return key


def fr(value: float, digits: int = 2) -> str:
    """French decimal notation."""
    return f"{value:.{digits}f}".replace(".", ",")


def fmt_int(value: float | None) -> str:
    """Grouped integer, French style: ``128 402``."""
    if value is None:
        return "—"
    return f"{round(value):,}".replace(",", THIN_SPACE)


def fmt_compact(value: float | None) -> str:
    """Short form for stat tiles: ``842``, ``128,4 k``, ``1,3 M``."""
    if value is None:
        return "—"
    number = float(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number < 1_000:
        return f"{sign}{round(number)}"
    if number < 1_000_000:
        return f"{sign}{fr(number / 1_000, 1)}{NBSP}k"
    return f"{sign}{fr(number / 1_000_000, 1)}{NBSP}M"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    """A 0–1 ratio as a French percentage."""
    if value is None:
        return "n/a"
    return f"{fr(value * 100, digits)}{NBSP}%"


def fmt_delta(value: float | None, digits: int = 1) -> str | None:
    """Signed relative change, or ``None`` when there is no comparison base.

    ``None`` rather than ``"n/a"``: Streamlit hides the delta row entirely when
    it gets ``None``, which is the honest rendering of "no previous period".
    """
    if value is None:
        return None
    return f"{'+' if value >= 0 else '−'}{fr(abs(value) * 100, digits)}{NBSP}%"


def fmt_points(value: float | None, digits: int = 1) -> str:
    """A rate *difference* in percentage points — never confused with a ratio."""
    if value is None:
        return "n/a"
    return f"{'+' if value >= 0 else '−'}{fr(abs(value) * 100, digits)}{NBSP}pt"


def fmt_date(moment: date | None) -> str:
    if moment is None:
        return "—"
    return f"{moment.day}{NBSP}{MONTHS_FR[moment.month - 1]}"


def fmt_period(start: date | None, end: date | None) -> str:
    """``12 mai → 10 juin``, with the year appended when the range crosses one."""
    if start is None or end is None:
        return "—"
    if start.year != end.year:
        return f"{fmt_date(start)}{NBSP}{start.year} → {fmt_date(end)}{NBSP}{end.year}"
    return f"{fmt_date(start)} → {fmt_date(end)}{NBSP}{end.year}"


def humanize_age(seconds: float | None) -> str:
    """
    Age in French, with minute resolution.

    Hour-only wording made a 15-minute refresh read as "moins d'1 h" forever,
    which is exactly as uninformative as showing nothing.
    """
    if seconds is None:
        return "—"
    seconds = max(seconds, 0)
    if seconds < 60:
        return "à l'instant"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"il y a {minutes} min"
    hours = int(seconds // 3600)
    if hours < 24:
        remainder = int((seconds % 3600) // 60)
        return f"il y a {hours} h" if remainder == 0 else f"il y a {hours} h {remainder:02d}"
    days = int(seconds // 86400)
    return "il y a 1 jour" if days == 1 else f"il y a {days} jours"
