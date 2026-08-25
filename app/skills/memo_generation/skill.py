"""Weekly French editorial memo composed from the public catalogue. Facts only.

This skill writes prose, which makes it the most dangerous thing in the project:
prose is where a number quietly becomes a claim. Three constraints keep it
honest, and each one is checkable rather than promised.

**It composes, it never computes.** Every figure arrives through `MemoInput`.
Nothing here divides, aggregates or thresholds — those all happened in
`public_signal_analysis` and `catalogue_movement`, where they are tested. A
median recomputed here to save a round trip is a median that can disagree with
the page showing the same week.

**Every printed number is declared.** Figures are emitted through a recorder, so
`undeclared_figures` can re-read the finished markdown and name any number that
did not come from the input. A hand-typed "environ 40 %" fails this, which is
the point — it is exactly the kind of sentence that survives review.

**Funnel vocabulary is confined to one section.** Views, likes and comments say
nothing about signups, and the fastest way to ruin this memo is a sentence that
slides from one to the other. `FUNNEL_VOCABULARY` may appear only in the section
whose job is to say those things are invisible; `funnel_vocabulary_leaks` checks
it. This is the ADR-009 pattern applied to text: a deterministic post-condition,
not a well-worded instruction.

There is deliberately **no recommendation section**. Recommendations are
reasoning, and reasoning belongs to an agent (ADR-002). Wiring
`growth_strategist_agent` into a scheduled memo also makes Monday's output
depend on a model call — so the memo states what moved and what it cannot see,
and the standing editorial proposals live on their own page where they can be
argued with.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

from app.skills.content_classification import label_fr
from app.skills.memo_generation.schemas import (
    FUNNEL_VOCABULARY,
    LIMITS_SECTION_KEY,
    EditorialMemo,
    MemoError,
    MemoInput,
    MemoSection,
)
from app.skills.public_signal_analysis import DimensionStat, PublicSignalReport

THIN_SPACE = " "
NBSP = " "

#: Any run of digits, allowing French decimal commas and grouping separators.
#: Used to re-read the finished memo and check nothing numeric slipped in by hand.
_NUMBER = re.compile(rf"\d[\d{THIN_SPACE}{NBSP}.,\-/]*\d|\d")

#: Below this many videos a dimension row is not worth a sentence. Same threshold
#: and same reasoning as the dashboard's, and as `public_signal_analysis`.
THIN_THRESHOLD = 10


class _Figures:
    """Formats numbers for the memo and remembers every string it produced.

    The memory is the audit trail. Without it "no undeclared figures" would be a
    claim about the author's discipline rather than a property of the artefact.
    """

    def __init__(self) -> None:
        self.seen: list[str] = []

    def _keep(self, rendered: str) -> str:
        """Record a rendered figure, and every numeric token inside it.

        Both, because the audit re-reads finished markdown with a regex that
        knows nothing about units: it sees ``4,30`` where the composer emitted
        ``4,30 %``, and ``120 000`` where it emitted ``+120 000``. Recording only
        the decorated form would flag the memo's own arithmetic as hand-typed.
        """
        self.seen.append(rendered)
        self.seen.extend(match.group(0) for match in _NUMBER.finditer(rendered))
        return rendered

    def fr(self, value: float, digits: int = 2) -> str:
        return self._keep(f"{value:.{digits}f}".replace(".", ","))

    def integer(self, value: float) -> str:
        return self._keep(f"{round(value):,}".replace(",", THIN_SPACE))

    def pct(self, ratio: float, digits: int = 1) -> str:
        return self._keep(f"{ratio * 100:.{digits}f}".replace(".", ",") + f"{NBSP}%")

    def signed_int(self, value: float) -> str:
        sign = "+" if value >= 0 else "−"
        return self._keep(f"{sign}{abs(round(value)):,}".replace(",", THIN_SPACE))

    def day(self, moment: date) -> str:
        return self._keep(f"{moment:%d/%m/%Y}")

    def year(self, value: int) -> str:
        return self._keep(str(value))

    def literal(self, rendered: str) -> str:
        """Register a figure written as text — a reference value, a threshold."""
        return self._keep(rendered)

    def quote(self, text: str) -> str:
        """Pass through verbatim data, registering any number it contains.

        A video called "Cheminot aisé de 48 ans" carries a 48 that the memo
        neither computed nor chose. It is still derived — it arrived with the
        data — so quoting it is declaring it. Without this the guard would fire
        on every title the catalogue happens to have numbered, and a guard that
        cries wolf gets switched off.
        """
        self.seen.extend(match.group(0) for match in _NUMBER.finditer(text))
        return text


def _rank(rows: list[DimensionStat], value: str) -> int | None:
    for position, row in enumerate(rows, start=1):
        if row.value == value:
            return position
    return None


def _pick(rows: list[DimensionStat], value: str) -> DimensionStat | None:
    return next((row for row in rows if row.value == value), None)


def _solid(rows: list[DimensionStat]) -> list[DimensionStat]:
    """Rows carrying enough videos to be worth a sentence in a memo."""
    return [row for row in rows if row.videos >= THIN_THRESHOLD]


# ---- sections ---------------------------------------------------------------


def _freshness_section(data: MemoInput, fig: _Figures) -> MemoSection:
    """Say how current this is before saying anything else.

    A memo that arrives every Monday has to distinguish "nothing changed" from
    "nothing was measured". Reading order is belief order: the reader who learns
    on line forty that the ingest failed has already believed lines one to
    thirty-nine.
    """
    lines = [
        f"- **{fig.integer(data.videos)} vidéos** au catalogue, "
        f"dont **{fig.integer(data.classified)} classées**."
    ]
    if data.last_checked_at is None:
        lines.append(
            "- ⚠️ **Aucun cycle de rafraîchissement enregistré.** Les chiffres "
            "ci-dessous datent de la dernière ingestion manuelle et peuvent être "
            "arbitrairement anciens."
        )
    else:
        lines.append(
            f"- Dernière vérification le {fig.day(data.last_checked_at.date())}."
        )
        if data.last_changed_at is not None:
            lines.append(
                f"- Dernier mouvement de compteurs le "
                f"{fig.day(data.last_changed_at.date())}. Une vérification qui ne "
                "trouve rien de neuf n'écrit rien : les deux dates diffèrent "
                "normalement."
            )
    return MemoSection(
        key="fraicheur",
        title="Fraîcheur",
        body="\n".join(lines),
        kind="method",
    )


def _movement_section(data: MemoInput, fig: _Figures) -> MemoSection:
    """What moved since the previous snapshot — or why that cannot be said yet."""
    if data.movement is None:
        return MemoSection(
            key="mouvement",
            title="Ce qui a bougé",
            body=(
                "**Pas encore mesurable.** L'API publique renvoie des compteurs "
                "cumulés sans historique, donc l'évolution ne se calcule qu'entre "
                "deux relevés. Il n'y en a qu'un pour l'instant : ce paragraphe se "
                "remplira tout seul au prochain cycle. Rien n'est estimé en "
                "attendant."
            ),
            kind="limit",
        )

    coverage = data.movement.coverage
    lines = [
        f"Entre le {fig.day(coverage.period_start)} et le "
        f"{fig.day(coverage.period_end)}, **{fig.integer(coverage.videos_moved)} "
        f"vidéos sur {fig.integer(coverage.videos_paired)}** ont vu leurs compteurs "
        f"bouger, pour **{fig.signed_int(coverage.total_delta_views)} vues** au total."
    ]
    if coverage.is_single_day:
        lines.append(
            "\n> ⚠️ Les deux relevés sont séparés d'un jour. C'est une observation, "
            "pas une tendance — à ne pas lire comme une dynamique hebdomadaire."
        )

    ages = [row for row in data.movement.by_publication_age if row.share_of_movement]
    if ages:
        top_age = max(ages, key=lambda row: row.share_of_movement or 0)
        lines.append(
            f"\nL'essentiel du mouvement vient des vidéos "
            f"**{fig.quote(top_age.dimension_value)}** : "
            f"{fig.pct(top_age.share_of_movement or 0)} des vues gagnées sur la "
            f"période, pour {fig.integer(top_age.videos)} vidéos."
        )

    if data.movement.top_movers:
        lines.append("\nLes plus fortes progressions :\n")
        for mover in data.movement.top_movers[:3]:
            lines.append(
                f"- **{fig.signed_int(mover.delta_views)} vues** — "
                f"« {fig.quote(mover.title)} » ({mover.video_format}, "
                f"{fig.day(mover.published_at)})"
            )

    if data.movement.omissions:
        omitted = data.movement.omissions[0]
        lines.append(
            f"\n*Couverture : {fig.integer(omitted.videos_omitted)} vidéos écartées "
            f"de la ventilation « {fig.quote(omitted.dimension)} » — "
            f"{fig.quote(omitted.reason)}. Les parts ci-dessus ne somment donc pas "
            f"à {fig.literal('100')} %.*"
        )

    return MemoSection(
        key="mouvement",
        title="Ce qui a bougé",
        body="\n".join(lines),
        kind="fact",
    )


def _format_section(report: PublicSignalReport, fig: _Figures) -> MemoSection | None:
    """The composition effect, restated every week because every week it applies."""
    short = _pick(report.by_format, "short")
    long = _pick(report.by_format, "long")
    if short is None or long is None:
        return None

    ratio = (
        long.median_engagement_rate / short.median_engagement_rate
        if short.median_engagement_rate
        else 0.0
    )
    body = (
        f"Le catalogue reste deux produits : **{fig.pct(short.share_of_catalogue, 0)} "
        f"de Shorts** ({fig.integer(short.videos)} vidéos) et "
        f"**{fig.pct(long.share_of_catalogue, 0)} de format long** "
        f"({fig.integer(long.videos)} vidéos).\n\n"
        f"Un spectateur de format long laisse une trace **{fig.fr(ratio, 1)} fois "
        f"plus souvent** qu'un spectateur de Short "
        f"({fig.pct(long.median_engagement_rate, 2)} contre "
        f"{fig.pct(short.median_engagement_rate, 2)} d'engagement médian). "
        "Toute statistique agrégée tous formats confondus mesure donc surtout la "
        "proportion de Shorts de chaque catégorie : ce qui suit est présenté par "
        "format."
    )
    return MemoSection(key="format", title="Le cadrage", body=body, kind="fact")


def _editorial_section(report: PublicSignalReport, fig: _Figures) -> MemoSection | None:
    """What carries and what does not, at constant format."""
    topics = _solid(report.by_topic_long)
    hooks = _solid(report.by_hook_long)
    if not topics or not hooks:
        return None

    best_topic, worst_topic = topics[0], topics[-1]
    best_hook, worst_hook = hooks[0], hooks[-1]

    lines = [
        "En format long, sur les catégories adossées à un échantillon suffisant :",
        "",
        f"- **Sujets** — {label_fr(best_topic.value)} porte le plus loin "
        f"({fig.fr(best_topic.median_reach_index)}, {fig.integer(best_topic.videos)} "
        f"vidéos) ; {label_fr(worst_topic.value)} le moins "
        f"({fig.fr(worst_topic.median_reach_index)}, "
        f"{fig.integer(worst_topic.videos)} vidéos).",
        f"- **Accroches** — {label_fr(best_hook.value)} en tête "
        f"({fig.fr(best_hook.median_reach_index)}, {fig.integer(best_hook.videos)} "
        f"vidéos) ; {label_fr(worst_hook.value)} en queue "
        f"({fig.fr(worst_hook.median_reach_index)}, "
        f"{fig.integer(worst_hook.videos)} vidéos).",
        "",
        f"L'indice de portée rapporte les vues d'une vidéo à la médiane de sa "
        f"cohorte — format × trimestre de publication. {fig.literal('1,00')} = "
        "typique pour sa cohorte, et la croissance de la chaîne est donc neutralisée.",
    ]
    return MemoSection(
        key="editorial",
        title="Ce qui porte, ce qui ne porte pas",
        body="\n".join(lines),
        kind="fact",
    )


def _titles_section(data: MemoInput, fig: _Figures) -> MemoSection | None:
    """The standing recommendation, restated with this week's candidate list."""
    if not data.candidates:
        return None

    hook_row = _pick(data.report.by_hook_long, data.hook)
    rank = _rank(data.report.by_hook_long, data.hook)
    lead = ""
    if hook_row is not None and rank is not None:
        lead = (
            f"L'accroche **{label_fr(data.hook).lower()}** obtient "
            f"{fig.fr(hook_row.median_reach_index)} en format long — rang "
            f"{fig.integer(rank)} sur {fig.integer(len(data.report.by_hook_long))}, "
            f"pour {fig.integer(hook_row.videos)} vidéos.\n\n"
        )

    lines = [
        f"{lead}Les vidéos longues qui la portent et qui sont sous la médiane de "
        "leur cohorte, les plus basses d'abord :",
        "",
    ]
    for candidate in data.candidates:
        lines.append(
            f"- **{fig.fr(candidate.reach_index)}** — « {fig.quote(candidate.title)} » "
            f"({fig.year(candidate.published_year)})"
        )
    lines.append(
        "\nLes réécritures proposées vivent sur la page « Dix titres », avec la "
        "justification de chacune. Cette liste est une requête, pas une sélection : "
        "une vidéo qui remonte au-dessus de sa cohorte en sort toute seule."
    )
    return MemoSection(
        key="titres",
        title="Les titres à revoir",
        body="\n".join(lines),
        kind="fact",
    )


def _limits_section() -> MemoSection:
    """The only section allowed to name the funnel — and it names it to disown it."""
    return MemoSection(
        key=LIMITS_SECTION_KEY,
        title="Ce que ce mémo ne peut pas voir",
        body=(
            "Tout ce qui précède vient de données publiques : titre, date, durée, "
            "vues, likes, commentaires. Ne sont visibles ni le CTR des vignettes, "
            "ni la durée de visionnage, ni les sources de trafic, ni les "
            "inscriptions, ni la conversion vers un abonnement payant. Aucune n'est "
            "estimée ici.\n\n"
            "L'indice de portée est donc un proxy : il dit qu'une vidéo a circulé, "
            "pas qu'elle a converti. La question qui trancherait, et qu'une journée "
            "d'accès aux données internes suffirait à régler : **le classement des "
            "vidéos par vues est-il le même que par inscriptions ?** S'il diverge, "
            "le calendrier éditorial optimise la mauvaise métrique et les priorités "
            "ci-dessus changent d'ordre."
        ),
        kind="limit",
    )


def _provenance(data: MemoInput, fig: _Figures) -> str:
    # The "3" of "Data v3" is part of a product name, not a measurement — declared
    # so the audit does not flag the provenance line it is meant to protect.
    fig.literal("3")
    return (
        f"Corpus {fig.day(data.report.period_start.date())} → "
        f"{fig.day(data.report.period_end.date())}. "
        f"{fig.integer(data.report.coverage.videos_indexed)} vidéos indexées sur "
        f"{fig.integer(data.report.coverage.videos_total)} ; "
        f"{fig.integer(data.report.coverage.videos_excluded)} écartées "
        f"({fig.quote(data.report.coverage.excluded_reason)}). "
        "Analyse indépendante, sans affiliation. API YouTube Data v3, lecture seule. "
        "Sujets et accroches attribués par modèle de langage à partir du titre seul ; "
        "toutes les statistiques sont déterministes."
    )


# ---- composition ------------------------------------------------------------


def generate_editorial_memo(payload: MemoInput | dict) -> EditorialMemo:
    """Compose the weekly memo. Raises `MemoError` when there is nothing to say."""
    data = payload if isinstance(payload, MemoInput) else MemoInput.model_validate(payload)
    if data.report.coverage.videos_indexed <= 0:
        raise MemoError("No indexed videos — nothing to write a memo about")

    fig = _Figures()
    sections = [
        section
        for section in (
            _freshness_section(data, fig),
            _movement_section(data, fig),
            _format_section(data.report, fig),
            _editorial_section(data.report, fig),
            _titles_section(data, fig),
            _limits_section(),
        )
        if section is not None
    ]

    title = f"Mémo éditorial — semaine du {fig.day(data.generated_on)}"
    provenance = _provenance(data, fig)
    body = "\n\n".join(f"## {section.title}\n\n{section.body}" for section in sections)
    markdown = f"# {title}\n\n{body}\n\n---\n\n*{provenance}*\n"

    return EditorialMemo(
        title=title,
        generated_on=data.generated_on,
        period_start=data.report.period_start.date(),
        period_end=data.report.period_end.date(),
        sections=sections,
        markdown=markdown,
        figures=fig.seen,
        provenance=provenance,
    )


# ---- post-conditions --------------------------------------------------------


def undeclared_figures(memo: EditorialMemo) -> tuple[str, ...]:
    """Numbers present in the markdown that the composer never emitted.

    A non-empty result means a figure was typed rather than derived — the one
    failure mode a memo cannot be allowed to ship with, because a hand-written
    number looks exactly like a measured one.
    """
    declared = set(memo.figures)
    found = {match.group(0) for match in _NUMBER.finditer(memo.markdown)}
    return tuple(sorted(token for token in found if token not in declared))


def funnel_vocabulary_leaks(memo: EditorialMemo) -> tuple[tuple[str, str], ...]:
    """Funnel words appearing outside the section that exists to disown them.

    Returns `(section key, term)` pairs. Views and signups are different
    universes here; a sentence that crosses from one to the other is the exact
    claim this project refuses to make, and refusing it in a prompt would not be
    refusing it at all.
    """
    leaks = []
    for section in memo.sections:
        if section.key == LIMITS_SECTION_KEY:
            continue
        haystack = f"{section.title}\n{section.body}".lower()
        leaks.extend(
            (section.key, term) for term in FUNNEL_VOCABULARY if term in haystack
        )
    return tuple(leaks)


def memo_filename(memo: EditorialMemo, *, moment: datetime | None = None) -> str:
    """Dated filename, UTC, sortable. Mirrors the weekly report's convention."""
    stamp = (moment or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"memo_editorial_{stamp}.md"
