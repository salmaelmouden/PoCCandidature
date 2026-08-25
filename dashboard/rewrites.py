"""Ten proposed title rewrites — editorial judgement, joined to live evidence.

Everything else in this project computes. This module does not, and says so: a
title is written, not derived. What *is* derived is which videos appear here —
the service picks them by reach index, so a proposal whose video has climbed out
of the bottom of the distribution disappears rather than sitting on the page
asserting a problem that has gone away.

Two rules constrain the writing, both visible in the output:

- **No invented figures.** Several rewrites move a number into the title,
  because that is the register the series wins in. The numbers themselves are
  not knowable from the public API, so they appear as ``[slots]`` for whoever
  has watched the video. A title with a plausible made-up euro amount in it
  would be worth less than nothing.
- **No asserted verdicts.** The rewrites restate a situation; they never claim
  an outcome about a real person's finances that the public data cannot support.

The rewrites are keyed by video id rather than by position, so re-ranking the
candidates cannot silently pair a proposal with the wrong original.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.public_signals import IndexedVideo, TitleEvidence
from dashboard.catalogue_view import THIN_THRESHOLD, label_of
from dashboard.formatting import fr

SLOT_NOTE = (
    "Les crochets sont des emplacements, pas des chiffres : le montant exact "
    "vient de la vidéo, que je n'ai pas regardée. Aucun nombre n'est inventé ici."
)


@dataclass(frozen=True)
class Rewrite:
    """One authored proposal for one specific video."""

    proposal: str
    rationale: str
    register: str
    precedent_id: str | None = None
    precedent_note: str | None = None


@dataclass(frozen=True)
class Proposal:
    """A rewrite joined to the live numbers of the video it targets."""

    youtube_video_id: str
    original: str
    proposal: str
    rationale: str
    register: str
    register_label: str
    reach_index: float
    published_year: int
    topic_label: str
    precedent: Precedent | None

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.youtube_video_id}"


@dataclass(frozen=True)
class Precedent:
    """An earlier video of the channel's own that already ran the comparison."""

    youtube_video_id: str
    title: str
    reach_index: float
    ratio: float
    note: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.youtube_video_id}"


#: Authored rewrites, keyed by the video they target.
REWRITES: dict[str, Rewrite] = {
    "LQflb9Y_O3g": Rewrite(
        proposal="Cheminot de 48 ans, [patrimoine] € de côté et pas un euro investi",
        rationale=(
            "Le profil est déjà là ; le chiffre manque. « Est-ce trop tard » demande "
            "au spectateur de trancher avant de lui avoir donné les termes — alors "
            "que la vidéo, elle, les donne."
        ),
        register="chiffre",
    ),
    "8CeJTs1Z55Q": Rewrite(
        proposal="[X] M€ de carrière, plus rien à 40 ans : ce que les sportifs font de leur argent",
        rationale=(
            "« Pourquoi » annonce une explication, et une explication n'est pas un "
            "enjeu. Le même sujet reformulé en écart chiffré retombe dans le registre "
            "où cette série gagne."
        ),
        register="chiffre",
    ),
    "2hcxOKnzKFI": Rewrite(
        proposal="Il rentre en France à 46 ans avec [patrimoine] € placés à l'étranger",
        rationale=(
            "« Doit-il tout vendre » délègue la décision au spectateur avant le "
            "contexte. La série marche quand le titre pose la situation et garde le "
            "verdict pour la vidéo."
        ),
        register="chiffre",
    ),
    "VvAcdJP9BX0": Rewrite(
        proposal="Valentin Demé : ce qui casse vraiment dans le marché crypto | Finary Talk #20",
        rationale=(
            "Sur un Talk, l'invité est l'actif du titre. L'autorité est l'accroche la "
            "mieux classée du format long — et un Talk n'est pas une analyse de "
            "patrimoine : le registre se choisit par sous-format, jamais par catalogue."
        ),
        register="autorite",
    ),
    "KwNLLx1PJcI": Rewrite(
        proposal="[X] % de son patrimoine sur un seul pays",
        rationale=(
            "La surexposition est déjà le sujet ; la chiffrer la rend vérifiable. "
            "« Est-il en danger » ajoute une alarme que le pourcentage porterait "
            "mieux tout seul."
        ),
        register="chiffre",
    ),
    "WczDda664nk": Rewrite(
        proposal="Arrêter à 56 ans : son plan, [patrimoine] € et [X] ans devant lui",
        rationale=(
            "Le titre actuel pose exactement la question à laquelle la vidéo répond. "
            "Celui-ci pose les termes du calcul : on clique pour le faire avec lui, "
            "pas pour recevoir un oui ou un non."
        ),
        register="chiffre",
    ),
    "SZEGxjm64Hw": Rewrite(
        proposal="Héritage de 230 000 € à 32 ans — sa décision",
        rationale=(
            "Le contre-exemple utile, et la raison de ne pas appliquer la règle "
            "mécaniquement. Le chiffre est déjà dans le titre et l'indice reste bas : "
            "ce n'est donc pas le chiffre qui manque. Ce qui coûte, c'est « investir "
            "ou profiter » — une alternative binaire qui transforme un cas concret en "
            "débat générique. Mettre un nombre ne suffit pas si le titre quitte la "
            "personne."
        ),
        register="chiffre",
    ),
    "LoqMzyT95hk": Rewrite(
        proposal="Frédéric Puzin (CEO Corum) : ce qui attend vraiment les SCPI | Finary Talk 47",
        rationale=(
            "Même invité, même sujet, deux titres — et un écart du simple au double. "
            "Les deux sont pourtant classés « question » : ce n'est donc pas le point "
            "d'interrogation qui coûte. L'un pose un enjeu, l'autre pose une question "
            "de manuel."
        ),
        register="autorite",
        precedent_id="xpbdkWAY5AE",
        precedent_note=(
            "Même invité, même classe d'actifs, seize mois plus tôt — et le même "
            "type d'accroche au classement."
        ),
    ),
    "Tw-HRXlVIa0": Rewrite(
        proposal="Un insider de la tech européenne : où va vraiment l'argent",
        rationale=(
            "La seconde moitié du titre porte déjà l'autorité ; la première la "
            "neutralise par une question de manuel. Inverser l'ordre suffit — c'est "
            "la réécriture la moins coûteuse des dix."
        ),
        register="autorite",
    ),
    "bY2P4DLT9Yg": Rewrite(
        proposal="Il investit son crédit étudiant en bourse à 19 ans",
        rationale=(
            "Le catalogue contient déjà la réponse : le même sujet, titré en "
            "affirmation quatre mois plus tôt. « Bonne idée ? » demande au spectateur "
            "de juger avant de savoir ; l'affirmation le fait cliquer pour vérifier."
        ),
        register="contrarian",
        precedent_id="7nShaXCBor8",
        precedent_note="Même sujet, quatre mois plus tôt, titré sans question.",
    ),
}


def _precedent(rewrite: Rewrite, evidence: TitleEvidence, reach_index: float) -> Precedent | None:
    """Resolve a cited earlier video against live data, or drop the citation.

    A precedent that has left the indexed set — its cohort fell under the
    reporting threshold, its classification changed — is omitted rather than
    rendered from a remembered number.
    """
    if rewrite.precedent_id is None:
        return None
    found = evidence.by_id(rewrite.precedent_id)
    if found is None or reach_index <= 0:
        return None
    return Precedent(
        youtube_video_id=found.signal.youtube_video_id,
        title=found.signal.title,
        reach_index=found.reach_index,
        ratio=found.reach_index / reach_index,
        note=rewrite.precedent_note or "",
    )


def _proposal(item: IndexedVideo, evidence: TitleEvidence) -> Proposal | None:
    rewrite = REWRITES.get(item.signal.youtube_video_id)
    if rewrite is None:
        return None
    return Proposal(
        youtube_video_id=item.signal.youtube_video_id,
        original=item.signal.title,
        proposal=rewrite.proposal,
        rationale=rewrite.rationale,
        register=rewrite.register,
        register_label=label_of(rewrite.register),
        reach_index=item.reach_index,
        published_year=item.signal.published_at.year,
        topic_label=label_of(item.signal.topic),
        precedent=_precedent(rewrite, evidence, item.reach_index),
    )


def proposals(evidence: TitleEvidence) -> tuple[Proposal, ...]:
    """Live candidates joined to authored rewrites, worst reach index first.

    A candidate with no rewrite written for it is skipped silently — the
    selection is data-driven and will surface new videos over time, and a blank
    proposal card would be worse than one card fewer. `unwritten` reports that
    count so the page can say it out loud instead of quietly showing nine.
    """
    return tuple(
        proposal
        for proposal in (_proposal(item, evidence) for item in evidence.candidates)
        if proposal is not None
    )


def unwritten(evidence: TitleEvidence) -> tuple[str, ...]:
    """Candidates the data surfaced but no rewrite has been written for yet."""
    return tuple(
        item.signal.title
        for item in evidence.candidates
        if item.signal.youtube_video_id not in REWRITES
    )


def gap_sentence(evidence: TitleEvidence, *, hook: str = "question") -> str | None:
    """The one-line statement of the gap the rewrites are aimed at.

    Built from both rankings because they disagree, and a reader who sees only
    the catalogue-wide one would draw the wrong rule.

    The register held up as the alternative is the best one that clears
    ``THIN_THRESHOLD``, not simply the top row. Inside the series the ranking is
    led by a category of eight videos, and a median over eight is not something
    to rewrite a publishing calendar on — the page says as much about its own
    tables, so the sentence must not quietly do the opposite.
    """
    overall = next((row for row in evidence.by_hook_long if row.value == hook), None)
    series = next((row for row in evidence.by_hook_series if row.value == hook), None)
    if overall is None or series is None:
        return None
    rank = next(
        (position for position, row in enumerate(evidence.by_hook_long, 1) if row.value == hook),
        None,
    )
    best_series = next(
        (row for row in evidence.by_hook_series if row.videos >= THIN_THRESHOLD), None
    )
    tail = ""
    if best_series is not None and best_series.value != hook:
        tail = (
            f" Dans la série récurrente, elle tombe à **{fr(series.median_reach_index)}** "
            f"({series.videos} vidéos) quand l'accroche "
            f"**{label_of(best_series.value).lower()}** atteint "
            f"**{fr(best_series.median_reach_index)}** ({best_series.videos} vidéos)."
        )
    return (
        f"En format long, l'accroche **{label_of(hook).lower()}** obtient un indice "
        f"médian de **{fr(overall.median_reach_index)}** — rang {rank} sur "
        f"{len(evidence.by_hook_long)}, pour {overall.videos} vidéos.{tail}"
    )
