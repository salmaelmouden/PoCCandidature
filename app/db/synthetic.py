"""Labelled synthetic dataset generator (deterministic given seed)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from random import Random

from app.db.constants import DATASET_LABEL, Channel, ExperimentStatus, Topic


@dataclass(frozen=True)
class SyntheticVideo:
    youtube_video_id: str
    title: str
    description: str
    published_at: datetime
    duration_seconds: int
    channel_id: str
    channel_title: str
    topic: str
    # Relative content quality knobs for generation
    reach_weight: float
    conversion_weight: float


@dataclass(frozen=True)
class SyntheticDailyMetric:
    youtube_video_id: str
    metric_date: date
    views: int
    likes: int
    comments: int


@dataclass(frozen=True)
class SyntheticAcquisition:
    metric_date: date
    channel: str
    topic: str
    youtube_video_id: str | None
    views: int
    visits: int
    signups: int
    activated_users: int
    premium_users: int


@dataclass(frozen=True)
class SyntheticUser:
    user_key: str
    signed_up_at: datetime
    activated_at: datetime | None
    became_premium_at: datetime | None
    channel: str
    topic: str
    youtube_video_id: str | None


@dataclass(frozen=True)
class SyntheticExperimentResult:
    variant: str
    users: int
    conversions: int
    conversion_rate: Decimal


@dataclass(frozen=True)
class SyntheticExperiment:
    experiment_key: str
    name: str
    hypothesis: str
    status: str
    primary_metric: str
    start_date: date
    end_date: date
    results: tuple[SyntheticExperimentResult, ...]


@dataclass(frozen=True)
class SyntheticSnapshot:
    snapshot_date: date
    period_start: date
    period_end: date
    metric_name: str
    metric_value: Decimal
    dimension_key: str
    dimensions: dict


@dataclass
class SyntheticDataset:
    """Fully labelled synthetic dataset for demos and tests."""

    label: str = DATASET_LABEL
    is_synthetic: bool = True
    as_of: date = field(default_factory=lambda: date.today())
    videos: list[SyntheticVideo] = field(default_factory=list)
    daily_metrics: list[SyntheticDailyMetric] = field(default_factory=list)
    acquisitions: list[SyntheticAcquisition] = field(default_factory=list)
    users: list[SyntheticUser] = field(default_factory=list)
    experiments: list[SyntheticExperiment] = field(default_factory=list)
    snapshots: list[SyntheticSnapshot] = field(default_factory=list)


_CHANNEL_BASE_VIEWS: dict[Channel, int] = {
    Channel.YOUTUBE: 4200,
    Channel.ORGANIC_SEARCH: 2800,
    Channel.LINKEDIN: 900,
    Channel.INSTAGRAM: 1500,
    Channel.PAID: 2200,
    Channel.DIRECT: 1100,
}

_TOPIC_TITLES: dict[Topic, list[str]] = {
    Topic.ETFS: [
        "ETF investing for beginners",
        "Why broad ETFs beat stock picking",
        "Building a simple ETF portfolio",
    ],
    Topic.STOCKS: [
        "How to read a stock chart",
        "Dividend stocks explained",
        "Common stock investing mistakes",
    ],
    Topic.CRYPTO: [
        "Crypto basics without the hype",
        "Bitcoin vs altcoins for beginners",
        "Managing crypto risk",
    ],
    Topic.PERSONAL_FINANCE: [
        "Your first wealth plan in 30 minutes",
        "Emergency fund: how much is enough?",
        "Net worth tracking that sticks",
    ],
    Topic.REAL_ESTATE: [
        "Buy vs rent: a practical framework",
        "REITs vs rental properties",
        "Mortgage basics for first-time buyers",
    ],
    Topic.BUDGETING: [
        "Zero-based budgeting in practice",
        "Cut expenses without feeling poor",
        "Automate your monthly budget",
    ],
}

# High reach / lower conversion topics vs lower reach / higher conversion
_TOPIC_REACH: dict[Topic, float] = {
    Topic.CRYPTO: 1.45,
    Topic.STOCKS: 1.15,
    Topic.ETFS: 1.0,
    Topic.PERSONAL_FINANCE: 0.95,
    Topic.REAL_ESTATE: 0.85,
    Topic.BUDGETING: 0.75,
}

_TOPIC_CONV: dict[Topic, float] = {
    Topic.CRYPTO: 0.65,
    Topic.STOCKS: 0.85,
    Topic.ETFS: 1.05,
    Topic.PERSONAL_FINANCE: 1.2,
    Topic.REAL_ESTATE: 1.0,
    Topic.BUDGETING: 1.35,
}


def generate_synthetic_dataset(
    *,
    seed: int = 42,
    days: int = 90,
    as_of: date | None = None,
) -> SyntheticDataset:
    """
    Generate a deterministic labelled synthetic dataset.

    Narrative baked in for later demos:
    - Last 14 days: YouTube premium conversion declines vs prior 14 days.
    - Crypto/Stocks: higher reach, weaker conversion.
    - Budgeting/Personal Finance: lower reach, stronger conversion.
    - One traffic anomaly spike ~21 days before as_of.
    """
    rng = Random(seed)
    end = as_of or date.today()
    start = end - timedelta(days=days - 1)
    decline_start = end - timedelta(days=13)

    videos = _build_videos(rng, start)
    daily_metrics = _build_daily_metrics(rng, videos, start, end)
    acquisitions = _build_acquisitions(rng, videos, start, end, decline_start)
    users = _build_users(rng, acquisitions)
    experiments = _build_experiments(end)
    snapshots = _build_snapshots(acquisitions, end)

    return SyntheticDataset(
        label=DATASET_LABEL,
        is_synthetic=True,
        as_of=end,
        videos=videos,
        daily_metrics=daily_metrics,
        acquisitions=acquisitions,
        users=users,
        experiments=experiments,
        snapshots=snapshots,
    )


def _build_videos(rng: Random, start: date) -> list[SyntheticVideo]:
    videos: list[SyntheticVideo] = []
    idx = 1
    for topic in Topic:
        for title in _TOPIC_TITLES[topic]:
            published = datetime(
                start.year,
                start.month,
                start.day,
                tzinfo=timezone.utc,
            ) + timedelta(days=rng.randint(0, 20), hours=rng.randint(8, 20))
            reach = _TOPIC_REACH[topic] * rng.uniform(0.85, 1.15)
            conv = _TOPIC_CONV[topic] * rng.uniform(0.9, 1.1)
            videos.append(
                SyntheticVideo(
                    youtube_video_id=f"syn{idx:04d}",
                    title=f"[SYNTHETIC] {title}",
                    description=(
                        "SYNTHETIC DATA — portfolio demo content. "
                        "Not affiliated with any real fintech company."
                    ),
                    published_at=published,
                    duration_seconds=rng.randint(360, 1200),
                    channel_id="SYNTHETIC_CHANNEL",
                    channel_title="Growth Intelligence Demo (Synthetic)",
                    topic=topic.value,
                    reach_weight=reach,
                    conversion_weight=conv,
                )
            )
            idx += 1
    return videos


def _build_daily_metrics(
    rng: Random,
    videos: list[SyntheticVideo],
    start: date,
    end: date,
) -> list[SyntheticDailyMetric]:
    anomaly_day = end - timedelta(days=21)
    rows: list[SyntheticDailyMetric] = []
    day = start
    while day <= end:
        weekend_factor = 0.72 if day.weekday() >= 5 else 1.0
        anomaly = 2.4 if day == anomaly_day else 1.0
        for video in videos:
            if day < video.published_at.date():
                continue
            age_days = (day - video.published_at.date()).days
            decay = max(0.25, 1.0 - (age_days * 0.015))
            views = int(
                800
                * video.reach_weight
                * weekend_factor
                * anomaly
                * decay
                * rng.uniform(0.85, 1.2)
            )
            likes = max(0, int(views * rng.uniform(0.03, 0.07)))
            comments = max(0, int(views * rng.uniform(0.004, 0.012)))
            rows.append(
                SyntheticDailyMetric(
                    youtube_video_id=video.youtube_video_id,
                    metric_date=day,
                    views=views,
                    likes=likes,
                    comments=comments,
                )
            )
        day += timedelta(days=1)
    return rows


def _build_acquisitions(
    rng: Random,
    videos: list[SyntheticVideo],
    start: date,
    end: date,
    decline_start: date,
) -> list[SyntheticAcquisition]:
    video_by_topic: dict[str, list[SyntheticVideo]] = {}
    for video in videos:
        video_by_topic.setdefault(video.topic, []).append(video)

    rows: list[SyntheticAcquisition] = []
    day = start
    while day <= end:
        weekend_factor = 0.75 if day.weekday() >= 5 else 1.0
        anomaly = 2.2 if day == end - timedelta(days=21) else 1.0
        in_decline = day >= decline_start

        for channel in Channel:
            for topic in Topic:
                topic_videos = video_by_topic[topic.value]
                base = _CHANNEL_BASE_VIEWS[channel] * _TOPIC_REACH[topic]
                views = int(base * weekend_factor * anomaly * rng.uniform(0.9, 1.1) / len(Topic))

                visit_rate = 0.18 if channel == Channel.YOUTUBE else 0.22
                if channel == Channel.PAID:
                    visit_rate = 0.28
                visits = max(0, int(views * visit_rate * rng.uniform(0.9, 1.05)))

                signup_rate = 0.08 * _TOPIC_CONV[topic]
                if channel == Channel.ORGANIC_SEARCH:
                    signup_rate *= 1.15
                if channel == Channel.INSTAGRAM:
                    signup_rate *= 0.7
                signups = max(0, int(visits * signup_rate * rng.uniform(0.9, 1.05)))

                activate_rate = 0.55
                activated = max(0, int(signups * activate_rate * rng.uniform(0.92, 1.05)))

                premium_rate = 0.12 * _TOPIC_CONV[topic]
                if channel == Channel.YOUTUBE:
                    premium_rate *= 0.55 if in_decline else 0.95
                elif channel == Channel.PAID:
                    premium_rate *= 0.9
                elif channel == Channel.ORGANIC_SEARCH:
                    premium_rate *= 1.1
                premium = max(0, int(activated * premium_rate * rng.uniform(0.9, 1.05)))

                if channel == Channel.YOUTUBE:
                    # Attribute YouTube acquisition to a topic video
                    video = topic_videos[day.toordinal() % len(topic_videos)]
                    # Scale row to one video share of topic
                    share_views = max(1, views)
                    rows.append(
                        SyntheticAcquisition(
                            metric_date=day,
                            channel=channel.value,
                            topic=topic.value,
                            youtube_video_id=video.youtube_video_id,
                            views=share_views,
                            visits=visits,
                            signups=signups,
                            activated_users=activated,
                            premium_users=premium,
                        )
                    )
                else:
                    rows.append(
                        SyntheticAcquisition(
                            metric_date=day,
                            channel=channel.value,
                            topic=topic.value,
                            youtube_video_id=None,
                            views=views,
                            visits=visits,
                            signups=signups,
                            activated_users=activated,
                            premium_users=premium,
                        )
                    )
        day += timedelta(days=1)
    return rows


def _build_users(rng: Random, acquisitions: list[SyntheticAcquisition]) -> list[SyntheticUser]:
    users: list[SyntheticUser] = []
    counter = 0
    # Sample users from signup days (keep volume bounded)
    for row in acquisitions:
        if row.signups <= 0:
            continue
        sample_n = min(row.signups, 3)
        for _ in range(sample_n):
            counter += 1
            signed = datetime(
                row.metric_date.year,
                row.metric_date.month,
                row.metric_date.day,
                hour=rng.randint(9, 21),
                tzinfo=timezone.utc,
            )
            activated_at = None
            premium_at = None
            if rng.random() < 0.55:
                activated_at = signed + timedelta(hours=rng.randint(1, 72))
                premium_prob = 0.08
                if row.channel == Channel.YOUTUBE.value:
                    # Mirror decline window
                    if row.metric_date >= acquisitions[-1].metric_date - timedelta(days=13):
                        premium_prob = 0.04
                    else:
                        premium_prob = 0.1
                if activated_at is not None and rng.random() < premium_prob:
                    premium_at = activated_at + timedelta(days=rng.randint(1, 14))
            users.append(
                SyntheticUser(
                    user_key=f"syn_user_{counter:06d}",
                    signed_up_at=signed,
                    activated_at=activated_at,
                    became_premium_at=premium_at,
                    channel=row.channel,
                    topic=row.topic,
                    youtube_video_id=row.youtube_video_id,
                )
            )
    return users


def _build_experiments(as_of: date) -> list[SyntheticExperiment]:
    return [
        SyntheticExperiment(
            experiment_key="syn_exp_youtube_cta",
            name="[SYNTHETIC] YouTube contextual Premium CTA",
            hypothesis=(
                "A more contextual Premium CTA on YouTube landing pages increases "
                "activated→premium conversion without hurting activation."
            ),
            status=ExperimentStatus.COMPLETED.value,
            primary_metric="activated_to_premium_rate",
            start_date=as_of - timedelta(days=45),
            end_date=as_of - timedelta(days=15),
            results=(
                SyntheticExperimentResult(
                    variant="control",
                    users=4200,
                    conversions=378,
                    conversion_rate=Decimal("0.090000"),
                ),
                SyntheticExperimentResult(
                    variant="treatment",
                    users=4180,
                    conversions=443,
                    conversion_rate=Decimal("0.105980"),
                ),
            ),
        )
    ]


def _build_snapshots(
    acquisitions: list[SyntheticAcquisition], as_of: date
) -> list[SyntheticSnapshot]:
    current_start = as_of - timedelta(days=13)
    previous_start = as_of - timedelta(days=27)
    previous_end = as_of - timedelta(days=14)

    def funnel(start: date, end: date, channel: str | None = None) -> dict[str, int]:
        totals = {
            "views": 0,
            "visits": 0,
            "signups": 0,
            "activated_users": 0,
            "premium_users": 0,
        }
        for row in acquisitions:
            if row.metric_date < start or row.metric_date > end:
                continue
            if channel is not None and row.channel != channel:
                continue
            totals["views"] += row.views
            totals["visits"] += row.visits
            totals["signups"] += row.signups
            totals["activated_users"] += row.activated_users
            totals["premium_users"] += row.premium_users
        return totals

    snapshots: list[SyntheticSnapshot] = []
    for label, start, end in (
        ("current_14d", current_start, as_of),
        ("previous_14d", previous_start, previous_end),
    ):
        overall = funnel(start, end)
        premium_rate = (
            Decimal(overall["premium_users"]) / Decimal(overall["activated_users"])
            if overall["activated_users"]
            else Decimal("0")
        )
        snapshots.append(
            SyntheticSnapshot(
                snapshot_date=as_of,
                period_start=start,
                period_end=end,
                metric_name="premium_conversion_rate",
                metric_value=premium_rate,
                dimension_key=f"overall:{label}",
                dimensions={"period": label, "channel": "all"},
            )
        )
        yt = funnel(start, end, Channel.YOUTUBE.value)
        yt_rate = (
            Decimal(yt["premium_users"]) / Decimal(yt["activated_users"])
            if yt["activated_users"]
            else Decimal("0")
        )
        snapshots.append(
            SyntheticSnapshot(
                snapshot_date=as_of,
                period_start=start,
                period_end=end,
                metric_name="premium_conversion_rate",
                metric_value=yt_rate,
                dimension_key=f"youtube:{label}",
                dimensions={"period": label, "channel": Channel.YOUTUBE.value},
            )
        )
    return snapshots
