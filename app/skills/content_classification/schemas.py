"""Taxonomy and contracts for LLM-backed content classification."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

CLASSIFICATION_VERSION = "v1"
"""Bump when the taxonomy or prompt changes — stored rows are keyed by it."""


class ContentTopic(StrEnum):
    """
    Editorial subject of a video.

    Built for a French personal-finance catalogue: the six generic topics in
    `app.db.constants.Topic` collapse most of it into "Personal Finance".
    """

    BOURSE_ACTIONS = "bourse_actions"
    ETF_GESTION_PASSIVE = "etf_gestion_passive"
    CRYPTO = "crypto"
    IMMOBILIER = "immobilier"
    FISCALITE = "fiscalite"
    EPARGNE_PLACEMENTS = "epargne_placements"
    RETRAITE = "retraite"
    MACRO_ACTUALITE = "macro_actualite"
    ENTREPRENEURIAT = "entrepreneuriat"
    PORTRAIT_HISTOIRE = "portrait_histoire"
    INTERVIEW = "interview"
    PRODUIT_FINARY = "produit_finary"
    EDUCATION_FINANCIERE = "education_financiere"


class HookType(StrEnum):
    """
    Rhetorical device the title leads with.

    This is the editorial dimension: it answers "which kind of promise makes
    people click", which reach and duration cannot.
    """

    QUESTION = "question"
    CHIFFRE = "chiffre"
    PROMESSE = "promesse"
    RECIT = "recit"
    AUTORITE = "autorite"
    ACTUALITE = "actualite"
    CURIOSITE = "curiosite"
    CONTRARIAN = "contrarian"


TOPIC_DEFINITIONS: dict[ContentTopic, str] = {
    ContentTopic.BOURSE_ACTIONS: "Actions, marchés boursiers, analyse d'entreprises cotées, indices.",
    ContentTopic.ETF_GESTION_PASSIVE: "ETF, trackers, fonds indiciels, DCA, gestion passive.",
    ContentTopic.CRYPTO: "Bitcoin, Ethereum, altcoins, blockchain, plateformes crypto.",
    ContentTopic.IMMOBILIER: "Achat, locatif, SCPI, crédit immobilier, marché du logement.",
    ContentTopic.FISCALITE: "Impôts, niches fiscales, succession, donation, optimisation fiscale.",
    ContentTopic.EPARGNE_PLACEMENTS: (
        "Assurance-vie, fonds euros, livrets, PEA, PER en tant que produits d'épargne, "
        "obligations, or, allocation patrimoniale."
    ),
    ContentTopic.RETRAITE: "Préparation de la retraite, pensions, indépendance financière, FIRE.",
    ContentTopic.MACRO_ACTUALITE: (
        "Inflation, taux, dette publique, politique économique, géopolitique, "
        "actualité économique et crises."
    ),
    ContentTopic.ENTREPRENEURIAT: "Créer/gérer une entreprise, business models, salaires, carrière.",
    ContentTopic.PORTRAIT_HISTOIRE: (
        "Récit centré sur une personne, une famille, une entreprise ou un épisode "
        "historique — la finance sert de décor à une histoire."
    ),
    ContentTopic.INTERVIEW: "Format entretien : un invité nommé est le sujet principal.",
    ContentTopic.PRODUIT_FINARY: "Fonctionnalités, annonces et démonstrations du produit Finary.",
    ContentTopic.EDUCATION_FINANCIERE: (
        "Pédagogie financière générale qui ne rentre dans aucune catégorie ci-dessus. "
        "À n'utiliser qu'en dernier recours."
    ),
}

HOOK_DEFINITIONS: dict[HookType, str] = {
    HookType.QUESTION: "Le titre pose une question au spectateur.",
    HookType.CHIFFRE: "Un montant, un pourcentage ou un classement chiffré porte l'accroche.",
    HookType.PROMESSE: "Un bénéfice ou un résultat concret est promis (gagner, économiser, réussir).",
    HookType.RECIT: "Le titre annonce une histoire, un parcours ou un épisode narratif.",
    HookType.AUTORITE: "Le nom d'un expert, d'une personnalité ou d'une institution porte l'accroche.",
    HookType.ACTUALITE: "Le titre s'appuie sur un événement daté ou une urgence.",
    HookType.CURIOSITE: "Le titre suggère un secret, une information cachée ou un mystère.",
    HookType.CONTRARIAN: "Le titre prend le contre-pied d'une idée reçue ou alerte sur une erreur.",
}


class VideoToClassify(BaseModel):
    """One classification input — title only, by design (see README)."""

    youtube_video_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class VideoClassificationResult(BaseModel):
    """One classification output."""

    youtube_video_id: str
    topic: ContentTopic
    hook_type: HookType


class ClassificationBatch(BaseModel):
    """Structured-output envelope — one entry per submitted video."""

    classifications: list[VideoClassificationResult]


class ClassifyContentResult(BaseModel):
    """Skill result."""

    requested: int
    classified: int
    skipped_already_done: int
    failed: int
    model: str
    version: str
    used_fallback: bool
