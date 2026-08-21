# Skill: content_classification

## Identity

- **Name:** `content_classification`
- **Module:** `app/skills/content_classification/`

## Purpose

Assign two editorial labels — `topic` and `hook_type` — to each ingested video title, so
content performance can be analysed by subject and by rhetorical device.

## Why an LLM here

The keyword classifier in `youtube_ingestion.transform.infer_topic` was measured against
the real Finary catalogue (952 videos, Aug 2026):

| Signal | Result |
|--------|--------|
| Videos falling into the `Personal Finance` fallback | **53 %** |
| Titles with no finance keyword at all, even with a 35-word FR vocabulary | **38 %** |
| Videos whose topic came from a description keyword absent from the title | 24 % (budget), 14 % (crypto) |

The 38 % blind spot is not random — it is the narrative catalogue (*« Toute une génération
ruinée en moins d'un mois »*, *« Les dépenses folles de Mike Tyson »*), precisely the
content whose performance is most interesting to compare. `hook_type` is not expressible
as keywords at all: a question mark is detectable, a *promise* is not.

Boundary: the LLM labels **text**. It never computes, aggregates or estimates a metric.
See [ADR-008](../../../docs/decisions/ADR-008-llm-text-labelling.md).

## Responsibility

- Does: classify titles, reconcile returned ids, persist versioned labels idempotently.
- Does **not**: compute metrics, read description text, overwrite `videos.topic`,
  invent videos, retry a failed batch silently.

## Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `dataset_label` | str | no | defaults to `youtube_api` |
| `batch_size` | int | no | 1–100, default 40 |
| `limit` | int \| None | no | ≥ 1; caps videos processed this run |
| `version` | str | no | defaults to `CLASSIFICATION_VERSION` |
| `force` | bool | no | re-classify rows already done at this version |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `requested` | int | Videos eligible this run |
| `classified` | int | Rows written |
| `skipped_already_done` | int | Already classified at this version |
| `failed` | int | Videos in batches that errored |
| `model` | str | Backend that produced the labels |
| `version` | str | Taxonomy/prompt version |
| `used_fallback` | bool | True when the keyword fallback ran |

## Taxonomy

13 topics (`ContentTopic`) and 8 hooks (`HookType`), defined in `schemas.py` with a
one-line French definition each — those definitions are injected verbatim into the prompt,
so the taxonomy and the prompt cannot drift apart.

Only the **title** is sent to the model. Descriptions are excluded deliberately: they carry
Finary's product pitch and UTM links, which is exactly what corrupted the keyword classifier.

## Determinism

- [ ] Fully deterministic for the same inputs
- [x] Partially deterministic (note external I/O)

`ClaudeClassifier` calls an external API and is not bit-reproducible. Reproducibility is
achieved by **persistence, not by re-running**: labels are written once per
`(video_id, version)` and every downstream analysis reads the stored row. Changing the
taxonomy or prompt requires bumping `CLASSIFICATION_VERSION`, which leaves prior rows intact.

`KeywordFallbackClassifier` is fully deterministic and used when no API key is present, so
CI and demos run offline. Its rows are stamped `classified_by = "keyword_fallback"` so the
analysis layer can exclude them.

## Side effects

Calls external API (Anthropic) · Writes DB (`video_classifications`, via repository).

Commits once per batch, so a failure late in a long run never discards work already paid for.

## Error handling

| Condition | Error / behavior |
|-----------|------------------|
| Missing API key | Warns, falls back to keyword classifier |
| Missing/empty model name | `ValueError` at construction |
| API/network failure on a batch | `ClassificationError` caught by the skill; batch counted in `failed`, run continues |
| Model returns an id that was not requested | Dropped with a warning — never assigned to another video |
| Model returns a duplicate id | First occurrence kept |
| Model omits ids | Logged; those videos stay unclassified and are retried on the next run |
| TLS interception (corporate proxy) | Set `CA_BUNDLE_PATH` to the system CA bundle |

## Tests

- Location: `app/skills/content_classification/tests/`
- Key cases: persistence, idempotency, `force`, dataset-label isolation, batch sizing,
  failed-batch reporting, hallucinated-id rejection, duplicate-id rejection, fallback
  selection and determinism.
- No API key required — the Claude backend is exercised through a stub.

## Example

```text
Input : "Partir à la retraite à 40 ans (frugalité & FIRE) | Victor Lora"
Output: topic=retraite  hook_type=promesse
        (keyword classifier said: ETFs)
```

## Run

```bash
python scripts/classify_content.py --limit 20     # sample first
python scripts/classify_content.py                # full catalogue
python scripts/classify_content.py --force        # re-classify at this version
```
