"""Skill: content_classification — LLM editorial labels for video titles."""

from app.skills.content_classification.classifier import (
    ClassificationError,
    Classifier,
    ClaudeClassifier,
    KeywordFallbackClassifier,
    build_classifier,
)
from app.skills.content_classification.schemas import (
    CLASSIFICATION_VERSION,
    HOOK_FR,
    TOPIC_FR,
    ClassifyContentResult,
    ContentTopic,
    HookType,
    VideoClassificationResult,
    VideoToClassify,
    label_fr,
)
from app.skills.content_classification.skill import (
    ClassifyContentRequest,
    classify_channel_content,
)

__all__ = [
    "CLASSIFICATION_VERSION",
    "HOOK_FR",
    "TOPIC_FR",
    "ClassificationError",
    "Classifier",
    "ClassifyContentRequest",
    "ClassifyContentResult",
    "ClaudeClassifier",
    "ContentTopic",
    "HookType",
    "KeywordFallbackClassifier",
    "VideoClassificationResult",
    "VideoToClassify",
    "build_classifier",
    "classify_channel_content",
    "label_fr",
]
