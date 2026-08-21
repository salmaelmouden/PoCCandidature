"""Classifier backends: Claude (primary) and a deterministic keyword fallback."""

from __future__ import annotations

import logging
from typing import Protocol

from app.skills.content_classification.prompts import SYSTEM_PROMPT, build_batch_prompt
from app.skills.content_classification.schemas import (
    ClassificationBatch,
    ContentTopic,
    HookType,
    VideoClassificationResult,
    VideoToClassify,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"


class ClassificationError(RuntimeError):
    """Raised when a batch cannot be classified."""


class Classifier(Protocol):
    """Backend contract — lets tests inject a fake without an API key."""

    name: str

    def classify_batch(
        self, videos: list[VideoToClassify]
    ) -> list[VideoClassificationResult]: ...


class ClaudeClassifier:
    """Claude-backed classifier using structured outputs (validated, not parsed by hand)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        effort: str = "medium",
        max_tokens: int = 16000,
        ca_bundle_path: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Anthropic API key is required")
        if not model:
            raise ValueError("Model name is required")
        # Imported lazily so the package stays importable without the LLM extra.
        import anthropic

        client_kwargs: dict = {"api_key": api_key}
        if ca_bundle_path:
            # Behind a TLS-intercepting proxy, certifi's bundle lacks the corporate
            # root CA. DefaultHttpxClient keeps the SDK's timeouts/limits intact.
            client_kwargs["http_client"] = anthropic.DefaultHttpxClient(verify=ca_bundle_path)
        self._client = anthropic.Anthropic(**client_kwargs)
        self._model = model
        self._effort = effort
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return self._model

    def classify_batch(
        self, videos: list[VideoToClassify]
    ) -> list[VideoClassificationResult]:
        if not videos:
            return []
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                output_config={"effort": self._effort},
                messages=[{"role": "user", "content": build_batch_prompt(videos)}],
                output_format=ClassificationBatch,
            )
        except Exception as exc:  # noqa: BLE001 — surfaced as a batch failure, not a crash
            raise ClassificationError(f"Claude classification failed: {exc}") from exc

        parsed = response.parsed_output
        if parsed is None:
            raise ClassificationError("Claude returned no parsed output")
        return self._reconcile(videos, parsed.classifications)

    @staticmethod
    def _reconcile(
        videos: list[VideoToClassify],
        results: list[VideoClassificationResult],
    ) -> list[VideoClassificationResult]:
        """
        Keep only ids we actually asked for.

        The model echoes ids back; a hallucinated or dropped id must not silently
        become a classification for the wrong video.
        """
        requested = {video.youtube_video_id for video in videos}
        seen: set[str] = set()
        kept: list[VideoClassificationResult] = []
        for result in results:
            if result.youtube_video_id not in requested:
                logger.warning(
                    "classification_unknown_id id=%s (dropped)", result.youtube_video_id
                )
                continue
            if result.youtube_video_id in seen:
                continue
            seen.add(result.youtube_video_id)
            kept.append(result)
        missing = requested - seen
        if missing:
            logger.warning("classification_missing_ids count=%s", len(missing))
        return kept


_TOPIC_KEYWORDS: tuple[tuple[ContentTopic, tuple[str, ...]], ...] = (
    (ContentTopic.ETF_GESTION_PASSIVE, ("etf", "tracker", "msci", "indiciel")),
    (ContentTopic.CRYPTO, ("crypto", "bitcoin", "ethereum", "btc", "blockchain")),
    (ContentTopic.IMMOBILIER, ("immobilier", "locatif", "scpi", "loyer", "logement")),
    (ContentTopic.FISCALITE, ("impôt", "impot", "fiscal", "succession", "donation")),
    (ContentTopic.RETRAITE, ("retraite", "pension")),
    (ContentTopic.EPARGNE_PLACEMENTS, ("assurance-vie", "fonds euros", "livret", "pea", "épargne")),
    (ContentTopic.BOURSE_ACTIONS, ("bourse", "action", "dividende", "cac 40", "nasdaq")),
    (ContentTopic.MACRO_ACTUALITE, ("inflation", "dette", "taux", "crise", "récession")),
    (ContentTopic.ENTREPRENEURIAT, ("entreprise", "startup", "business", "salaire")),
    (ContentTopic.PRODUIT_FINARY, ("finary",)),
)


class KeywordFallbackClassifier:
    """
    Deterministic fallback so demos and CI run without an API key.

    Deliberately weak: it exists to keep the pipeline runnable, not to produce
    analysable labels. Rows it writes are marked with this backend name so the
    analysis layer can exclude them.
    """

    name = "keyword_fallback"

    def classify_batch(
        self, videos: list[VideoToClassify]
    ) -> list[VideoClassificationResult]:
        return [
            VideoClassificationResult(
                youtube_video_id=video.youtube_video_id,
                topic=self._topic(video.title),
                hook_type=self._hook(video.title),
            )
            for video in videos
        ]

    @staticmethod
    def _topic(title: str) -> ContentTopic:
        haystack = title.lower()
        for topic, keywords in _TOPIC_KEYWORDS:
            if any(keyword in haystack for keyword in keywords):
                return topic
        return ContentTopic.EDUCATION_FINANCIERE

    @staticmethod
    def _hook(title: str) -> HookType:
        stripped = title.strip()
        if stripped.endswith("?"):
            return HookType.QUESTION
        if any(char.isdigit() for char in stripped):
            return HookType.CHIFFRE
        return HookType.CURIOSITE


def build_classifier(
    api_key: str | None,
    *,
    model: str = DEFAULT_MODEL,
    ca_bundle_path: str | None = None,
) -> Classifier:
    """Claude when a key is available, deterministic fallback otherwise."""
    if api_key:
        return ClaudeClassifier(api_key, model=model, ca_bundle_path=ca_bundle_path)
    logger.warning(
        "ANTHROPIC_API_KEY missing — falling back to keyword classification. "
        "Labels will be low quality and are marked as such in the database."
    )
    return KeywordFallbackClassifier()
