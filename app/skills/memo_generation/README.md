# Skill: memo_generation

## Identity

- **Name:** `memo_generation`
- **Module:** `app/skills/memo_generation/`

## Purpose

Compose the weekly French editorial memo over the **real** public catalogue: what moved,
what carries and what does not at constant format, which titles are due a rewrite, and
what the memo cannot see.

## Responsibility

- Does: compose French prose from figures it is handed, and expose two post-conditions
  that let a caller verify the result before shipping it.
- Does **not**: access the DB, call an LLM, compute a median, apply a threshold, estimate
  signups or conversion, or recommend.

## Why it computes nothing

Every figure arrives through `MemoInput`. The medians, cohort normalisation and movement
deltas all happened in `public_signal_analysis` and `catalogue_movement`, where they are
tested. A number recomputed here to save a round trip is a number that can disagree with
the dashboard page describing the same week — and the memo is the artefact that leaves the
building, so it is the worst place for that to happen.

## Why there is no recommendation section

Recommendations are reasoning, and reasoning belongs to an agent (ADR-002). Wiring
`growth_strategist_agent` into a scheduled job would also make Monday's delivery depend on
a model call succeeding. The memo therefore states what moved and what it cannot see; the
standing editorial proposals live on the **Dix titres** page, where each carries its own
justification and can be argued with.

## Post-conditions

Both are deterministic, and both are enforced by the CLI and the API **before** the memo is
written or returned. This is the ADR-009 pattern applied to text: the guarantee must not
depend on the author remembering, any more than W2's guarantee depends on a model obeying
a prompt.

| Function | Guarantees |
|---|---|
| `undeclared_figures(memo)` | Every number in the markdown was emitted by the composer or arrived inside quoted data. A hand-typed "environ 40 %" is named and the memo is rejected. |
| `funnel_vocabulary_leaks(memo)` | `FUNNEL_VOCABULARY` appears only in the section whose job is to say those things are invisible from outside a channel. |

The second one exists because the fastest way to ruin this memo is one sentence sliding
from "this video travelled" to "this video converted". Views, likes and comments say
nothing about signups, and no amount of careful wording makes that safe — so the check is
mechanical.

## Degradation

Absence is rendered as a sentence, never as a zero.

- **No second snapshot** — "Pas encore mesurable", with the reason. Movement needs two
  observations and a fresh deploy has one.
- **One-day resolution** — the movement section says it is an observation, not a trend.
- **No refresh run recorded** — the freshness section warns that the figures may be
  arbitrarily old, rather than implying they are current.
- **Thin dimension rows** — anything under `THIN_THRESHOLD` videos gets no sentence, so a
  median over four videos cannot become "the best performing topic".
- **Empty catalogue** — `MemoError`, rather than a memo about nothing.

## Contract

```text
generate_editorial_memo(MemoInput) -> EditorialMemo   # raises MemoError
undeclared_figures(EditorialMemo)  -> tuple[str, ...]
funnel_vocabulary_leaks(EditorialMemo) -> tuple[tuple[str, str], ...]
memo_filename(EditorialMemo)       -> str
```

## Surfaces

- `make memo` / `make memo-write` / `make memo-loop` → `scripts/generate_editorial_memo.py`
- `POST /api/memo/editorial` → 409 on an empty catalogue, 500 if a post-condition fails
- Dated markdown under `reports/`
