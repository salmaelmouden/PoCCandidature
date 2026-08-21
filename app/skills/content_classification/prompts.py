"""Prompt construction for content classification."""

from __future__ import annotations

from app.skills.content_classification.schemas import (
    HOOK_DEFINITIONS,
    TOPIC_DEFINITIONS,
    VideoToClassify,
)


def _definition_block(definitions: dict) -> str:
    return "\n".join(f"- `{key.value}` — {text}" for key, text in definitions.items())


SYSTEM_PROMPT = f"""Tu classes des titres de vidéos YouTube d'une chaîne francophone de finance personnelle.

Pour chaque vidéo, tu renvoies deux étiquettes.

## 1. `topic` — le sujet éditorial

{_definition_block(TOPIC_DEFINITIONS)}

Règles :
- Choisis le sujet **principal**, pas un sujet mentionné en passant.
- `education_financiere` est un dernier recours : ne l'utilise que si aucune autre \
catégorie ne convient vraiment.
- Un titre qui raconte l'histoire d'une personne ou d'une entreprise est \
`portrait_histoire`, même s'il parle d'argent.
- `interview` seulement si le format entretien est explicite (un invité nommé est le sujet).

## 2. `hook_type` — le ressort de l'accroche

{_definition_block(HOOK_DEFINITIONS)}

Règles :
- Un seul hook : celui qui **porte** le titre, pas tous ceux qui sont présents.
- Un titre qui se termine par « ? » n'est `question` que si la question est le ressort \
principal ; s'il promet surtout un bénéfice, c'est `promesse`.
- La présence d'un chiffre ne suffit pas pour `chiffre` : il faut que le chiffre soit \
l'accroche (« 400 000 € », « les 3 erreurs »), pas un simple détail de contexte.

Tu renvoies exactement une entrée par vidéo soumise, avec son `youtube_video_id` inchangé.
Tu ne commentes pas, tu ne justifies pas."""


def build_batch_prompt(videos: list[VideoToClassify]) -> str:
    """Render one batch of videos as a numbered list for the model."""
    lines = [
        f"{index}. [{video.youtube_video_id}] {video.title}"
        for index, video in enumerate(videos, start=1)
    ]
    return (
        f"Classe ces {len(videos)} titres de vidéos.\n\n"
        + "\n".join(lines)
        + "\n\nRenvoie une entrée par vidéo, dans le même ordre."
    )
