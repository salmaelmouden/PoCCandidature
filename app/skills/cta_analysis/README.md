# Skill: `cta_analysis`

Reads the **entry point to the funnel** from public video descriptions: whether a
link to the product exists, whether it is visible before the reader expands the
description, and whether it carries anything an analytics tool could attribute a
signup to.

## The boundary

This skill measures **placement**, never conversion. Signups, clicks and
click-through rate are not observable from outside a channel and are never
estimated here. What it can say is *"this share of the catalogue offers no entry
point"*; what it can never say is *"this share of viewers did not sign up"*.

That distinction is what makes the reading possible at all: placement is the one
part of the acquisition path a channel publishes.

## Decisions worth knowing

| Decision | Why |
|---|---|
| Only `http(s)://` and `www.` URLs count | The same rule YouTube applies. A bare `example.com` mid-sentence is text, not a link — counting it would overstate what a viewer can click. |
| Product domain is **derived**, not configured | The most-linked domain outside YouTube and the social platforms. Returned with the sentence justifying it, so a page shows its assumption rather than asserting it. |
| Social and platform domains are labelled, not hidden | A channel linking its Instagram in every description would otherwise be told its product is Instagram. They stay in the domain table, marked. |
| Above the fold is counted in **rendered lines** | YouTube collapses by line, not by character: a paragraph of short lines buries a link at a small character offset. The raw offset ships too, so the threshold is auditable. |
| Redirectors are `OPAQUE`, not `UNTRACKED` | A `go.` sub-domain or a shortener can append a campaign parameter after the hop. Folding those into "untracked" would manufacture a finding out of something the URL text cannot settle. |
| No classifier required | Descriptions exist for every ingested video, so this reading covers the whole catalogue rather than the classified subset the reach index is limited to. |

## Output

`CtaReport` — coverage, the domain table, placement counts overall / per format /
per publication year, and the most frequent call-to-action wordings with their
URLs replaced by a placeholder so one template is not counted as many.

Every `PlacementStat` keeps each numerator beside its own denominator:
`with_primary` is a share of the slice, `above_fold` is a share of the videos in
it that carry a link. Ratios are properties, so a caller cannot divide by the
wrong one.

## Tests

`tests/test_cta_analysis.py` — pure, no DB, no network.
