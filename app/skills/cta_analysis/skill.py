"""Deterministic reading of the call-to-action in public video descriptions.

**The boundary.** Everything here is placement: does a link to the product
exist, is it visible before the description is expanded, does it carry anything
attributable. Not one number in this module is a conversion, a signup or a
click-through — none of the three is observable from outside a channel, and the
whole point of reading placement is that it is the part of the acquisition path
that *is* public.

What it can therefore say: "this share of the catalogue offers no entry point".
What it can never say: "this share of viewers did not sign up".
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from math import ceil
from statistics import median
from urllib.parse import parse_qsl, urlparse

from app.skills.cta_analysis.schemas import (
    FOLD_LINES,
    WRAP_COLUMNS,
    CtaCoverage,
    CtaLineStat,
    CtaReport,
    DomainStat,
    LinkKind,
    LinkPlacement,
    PlacementStat,
    TrackingState,
    VideoDescription,
)

URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]«»\"']+", re.IGNORECASE)
"""What YouTube itself turns into a clickable link.

A bare ``finary.com`` in the middle of a sentence is not a link on the watch
page — it is text. Matching only schemes and ``www.`` is not a shortcut around
harder parsing: it is the same rule the platform applies, so the count matches
what a viewer can actually click.
"""

_TRAILING = ".,;:!?… '\"»)]"

LINK_PLACEHOLDER = "‹lien›"

PLATFORM_SUFFIXES: tuple[str, ...] = ("youtube.com", "youtu.be")
"""Self-links. Every catalogue is full of them and none of them is a product CTA."""

SOCIAL_DOMAINS: frozenset[str] = frozenset(
    {
        "instagram.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "tiktok.com",
        "facebook.com",
        "threads.net",
        "discord.gg",
        "discord.com",
        "t.me",
        "reddit.com",
        "twitch.tv",
        "open.spotify.com",
        "spotify.com",
        "podcasts.apple.com",
        "apple.co",
        "deezer.com",
    }
)
"""Audience destinations, excluded from product-domain candidacy.

A channel that links its Instagram in all 950 descriptions would otherwise be
told its product is Instagram. Excluded, not hidden: they still appear in the
domain table, labelled, so the choice of primary domain is checkable.
"""

SHORTENER_DOMAINS: frozenset[str] = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "linktr.ee",
        "lnk.to",
        "app.link",
        "onelink.me",
        "smarturl.it",
        "buff.ly",
        "trib.al",
        "rebrand.ly",
        "shorturl.at",
    }
)

SHORTENER_PREFIXES: tuple[str, ...] = ("go.", "link.", "links.", "trk.", "click.", "r.")
"""Sub-domains conventionally used as redirectors, which may track server-side."""

TRACKING_PARAMS: frozenset[str] = frozenset(
    {
        "ref",
        "referrer",
        "source",
        "src",
        "via",
        "campaign",
        "aff",
        "affiliate",
        "code",
        "promo",
        "coupon",
        "fpr",
        "gclid",
        "fbclid",
        "irclickid",
        "mc_cid",
    }
)

TRACKING_PREFIXES: tuple[str, ...] = ("utm_", "mtm_", "pk_")


class CtaAnalysisError(ValueError):
    """Raised when the input set cannot be analysed."""


class ExtractedLink:
    """One clickable URL found in a description, with where it sits."""

    __slots__ = ("domain", "kind", "offset", "url")

    def __init__(self, url: str, domain: str, kind: LinkKind, offset: int) -> None:
        self.url = url
        self.domain = domain
        self.kind = kind
        self.offset = offset


def normalise_domain(url: str) -> str:
    """Host of a URL, lowercased, without ``www.`` or a port. ``""`` if unparseable."""
    candidate = url if "://" in url else f"https://{url}"
    host = (urlparse(candidate).hostname or "").lower()
    return host.removeprefix("www.")


def classify_domain(domain: str) -> LinkKind:
    """Whether a domain may stand for the product, and if not, why not."""
    if any(domain == suffix or domain.endswith(f".{suffix}") for suffix in PLATFORM_SUFFIXES):
        return LinkKind.PLATFORM
    if any(domain == social or domain.endswith(f".{social}") for social in SOCIAL_DOMAINS):
        return LinkKind.SOCIAL
    return LinkKind.PRODUCT


def _is_redirector(domain: str) -> bool:
    return domain in SHORTENER_DOMAINS or domain.startswith(SHORTENER_PREFIXES)


def tracking_state(url: str) -> TrackingState:
    """Read attribution off the URL text — and admit when the text cannot say.

    A redirector is reported as opaque rather than untracked: it may well append
    a campaign parameter after the hop, and that is invisible from here.
    """
    query = urlparse(url if "://" in url else f"https://{url}").query
    keys = {key.lower() for key, _ in parse_qsl(query, keep_blank_values=True)}
    if any(key in TRACKING_PARAMS or key.startswith(TRACKING_PREFIXES) for key in keys):
        return TrackingState.TRACKED
    if _is_redirector(normalise_domain(url)):
        return TrackingState.OPAQUE
    return TrackingState.UNTRACKED


def extract_links(text: str) -> list[ExtractedLink]:
    """Every clickable URL in a description, in reading order."""
    links: list[ExtractedLink] = []
    for match in URL_PATTERN.finditer(text or ""):
        url = match.group(0).rstrip(_TRAILING)
        if not url:
            continue
        domain = normalise_domain(url)
        if not domain:
            continue
        links.append(ExtractedLink(url, domain, classify_domain(domain), match.start()))
    return links


def rendered_line_of(text: str, offset: int) -> int:
    """How many rendered lines precede ``offset`` once the text is wrapped.

    Counted rather than derived from the character offset alone, because
    YouTube collapses the description by line: a paragraph of short lines
    pushes a link out of view long before a character budget would.
    """
    prefix = text[:offset]
    source_lines = prefix.split("\n")
    rendered = sum(max(1, ceil(len(line) / WRAP_COLUMNS)) for line in source_lines[:-1])
    return rendered + len(source_lines[-1]) // WRAP_COLUMNS


def cta_template(text: str, offset: int) -> str:
    """The line carrying the link, with every URL replaced by a placeholder.

    The URL is removed on purpose: two videos sharing a wording but carrying
    different campaign codes are the same editorial template, and counting the
    raw lines would report them as two.
    """
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    line = text[start:] if end == -1 else text[start:end]
    return " ".join(URL_PATTERN.sub(LINK_PLACEHOLDER, line).split())


def pick_primary_domain(
    videos: list[VideoDescription],
    links_by_video: dict[str, list[ExtractedLink]],
) -> tuple[str | None, str]:
    """The catalogue's product domain: the non-platform, non-social one it links most.

    Derived rather than configured so the reading works on any channel, and
    returned with the sentence that justifies it so a page can show its own
    assumption instead of asserting it.
    """
    counts: Counter[str] = Counter()
    for video in videos:
        domains = {
            link.domain
            for link in links_by_video[video.youtube_video_id]
            if link.kind is LinkKind.PRODUCT
        }
        counts.update(domains)
    if not counts:
        return None, "aucun domaine hors plateforme et hors réseaux sociaux dans le catalogue"
    # Alphabetical tie-break: two domains on the same count must not swap places
    # between two runs on identical data.
    domain, videos_linking = min(counts.items(), key=lambda item: (-item[1], item[0]))
    return domain, (
        f"domaine le plus lié du catalogue hors YouTube et réseaux sociaux — "
        f"{videos_linking} vidéos sur {len(videos)}"
    )


def _place(
    video: VideoDescription,
    links: list[ExtractedLink],
    primary_domain: str | None,
) -> LinkPlacement:
    """One video's placement record. Absent link and absent description differ."""
    primary = next(
        (
            link
            for link in links
            if primary_domain is not None
            and (link.domain == primary_domain or link.domain.endswith(f".{primary_domain}"))
        ),
        None,
    )
    base = {
        "youtube_video_id": video.youtube_video_id,
        "title": video.title,
        "video_format": video.video_format,
        "published_year": video.published_year,
        "views": video.views,
        "described": bool(video.description.strip()),
        "links_total": len(links),
    }
    if primary is None:
        return LinkPlacement(**base, has_primary=False)

    line = rendered_line_of(video.description, primary.offset)
    return LinkPlacement(
        **base,
        has_primary=True,
        first_offset=primary.offset,
        rendered_line=line,
        above_fold=line < FOLD_LINES,
        tracking=tracking_state(primary.url),
        primary_url=primary.url,
        cta_line=cta_template(video.description, primary.offset),
    )


def aggregate_placements(value: str, placements: list[LinkPlacement]) -> PlacementStat:
    """Fold one slice into counts. Every numerator keeps its own denominator."""
    with_primary = [item for item in placements if item.has_primary]
    offsets = [item.first_offset for item in with_primary if item.first_offset is not None]
    return PlacementStat(
        value=value,
        videos=len(placements),
        with_primary=len(with_primary),
        above_fold=sum(1 for item in with_primary if item.above_fold),
        tracked=sum(1 for item in with_primary if item.tracking is TrackingState.TRACKED),
        views=sum(item.views for item in placements),
        views_with_primary=sum(item.views for item in with_primary),
        views_above_fold=sum(item.views for item in with_primary if item.above_fold),
        median_offset=round(median(offsets), 1) if offsets else None,
    )


def analyse_cta(
    videos: list[VideoDescription],
    *,
    primary_domain: str | None = None,
    top_domains: int = 20,
    top_cta_lines: int = 8,
) -> CtaReport:
    """Build the placement evidence table. Facts only — no interpretation, by design.

    ``top_domains`` and ``top_cta_lines`` truncate two long tails for display;
    the full counts they were cut from are carried in ``coverage`` so a reader
    can see what the head is a head *of*.
    """
    if not videos:
        raise CtaAnalysisError("No descriptions to analyse")

    links_by_video = {
        video.youtube_video_id: extract_links(video.description) for video in videos
    }
    resolved_domain, reason = (
        pick_primary_domain(videos, links_by_video)
        if primary_domain is None
        else (primary_domain, "domaine fourni par l'appelant")
    )

    placements = [
        _place(video, links_by_video[video.youtube_video_id], resolved_domain)
        for video in videos
    ]

    domain_videos: Counter[str] = Counter()
    for links in links_by_video.values():
        domain_videos.update({link.domain for link in links})
    domains = [
        DomainStat(
            domain=domain,
            kind=classify_domain(domain),
            videos=count,
            share_of_catalogue=round(count / len(videos), 4),
        )
        for domain, count in sorted(domain_videos.items(), key=lambda item: (-item[1], item[0]))[
            :top_domains
        ]
    ]

    lines: Counter[str] = Counter(
        item.cta_line for item in placements if item.cta_line
    )

    by_format: dict[str, list[LinkPlacement]] = defaultdict(list)
    by_year: dict[str, list[LinkPlacement]] = defaultdict(list)
    for item in placements:
        by_format[item.video_format.value].append(item)
        by_year[str(item.published_year)].append(item)

    return CtaReport(
        period_start=min(video.published_at for video in videos),
        period_end=max(video.published_at for video in videos),
        coverage=CtaCoverage(
            videos_total=len(videos),
            described=sum(1 for item in placements if item.described),
            with_any_link=sum(1 for item in placements if item.links_total > 0),
            with_primary=sum(1 for item in placements if item.has_primary),
            primary_domain=resolved_domain,
            primary_domain_reason=reason,
        ),
        domains=domains,
        overall=aggregate_placements("catalogue", placements),
        # Shorts first: they are the majority of a modern catalogue and the slice
        # a description reading is usually about.
        by_format=[
            aggregate_placements(value, rows)
            for value, rows in sorted(by_format.items(), key=lambda item: item[0], reverse=True)
        ],
        by_year=[
            aggregate_placements(value, rows)
            for value, rows in sorted(by_year.items(), key=lambda item: item[0])
        ],
        cta_lines=[
            CtaLineStat(template=template, videos=count)
            for template, count in lines.most_common(top_cta_lines)
        ],
        placements=placements,
    )
