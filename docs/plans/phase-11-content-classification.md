# Plan: Phase 11 — LLM content classification

**Status:** Implemented
**Branch:** `phase-11-content-classification`
**Scope:** `content_classification` skill (topic + hook_type), versioned `video_classifications`
table, real Finary catalogue ingest, CLI + Makefile target, ADR-008.
**Out of scope:** the public-signal analytics that consume these labels (Phase 12), dashboard pages.

## Why

The project shipped ten phases of "AI-native growth analytics" without a single LLM call —
the agents are deterministic rule engines. Two problems converge here:

1. **Credibility.** The README claims AI-native; `grep -riE "anthropic|openai|claude"` returned
   zero hits across the codebase.
2. **A dead dimension.** Measured on the real Finary catalogue (952 videos):
   53 % of videos fell into the `Personal Finance` fallback, and 38 % of titles contain no
   finance keyword at all even against a 35-word French vocabulary. Topic was unusable, and
   `hook_type` — the only editorial signal in the project — did not exist.

Phase 10 fixes both with the same change, and draws the boundary explicitly in ADR-008:
**the LLM labels text; it never produces numbers.**

## Flow

```text
videos (dataset_label=youtube_api)
        → content_classification skill (title only)
            → ClaudeClassifier   (claude-opus-5, structured outputs)
            → KeywordFallback    (deterministic, no key needed)
        → video_classifications (versioned, attributed)
        → [Phase 12] public-signal analytics
```

## Decisions

- **Title only, never the description.** Descriptions carry Finary's product pitch and UTM
  links — measured to be exactly what corrupted the keyword classifier (24 % of videos matched
  "budget" in the description but not the title, 14 % matched "crypto").
- **Separate table, not `videos.topic`.** Keeps the keyword topic intact for comparison and
  makes the classification versioned rather than destructive.
- **Reproducibility by persistence, not by re-running.** See ADR-008.

## DoD

- [x] `content_classification` skill + 12 tests (no API key required)
- [x] `video_classifications` table + migration `002`
- [x] Repository methods + `VideoRepository.list_by_dataset_label`
- [x] CLI `scripts/classify_content.py` + `make classify`
- [x] Real Finary catalogue ingested (952 videos) and classified
- [x] ADR-008 amending ADR-002
- [x] Skill contract README

## Incidental fixes

Both surfaced while running against the real environment and both matter on deploy:

- **API key leaked into logs.** `httpx` logs full request URLs at INFO, so `YOUTUBE_API_KEY`
  was printed on every request. Silenced in both ingest scripts.
- **Empty `.env` placeholders overrode defaults.** `LLM_MODEL=` resolved to `""` and was sent
  to the API as the model name. Settings now coerce blank placeholders to unset.
- **Corporate TLS interception.** Zscaler re-signs `api.anthropic.com`; Python's certifi bundle
  lacks the corporate root CA, so requests failed while `curl` succeeded. Configurable via
  `CA_BUNDLE_PATH`.
