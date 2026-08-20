"""Schemas for content_analysis skill."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContentMetrics(BaseModel):
    """Per-content performance inputs for value scoring and ranking."""

    content_id: str
    title: str = ""
    topic: str
    reach: int = Field(ge=0, description="Views or equivalent reach")
    engagement: int = Field(ge=0, description="Likes + comments (or similar)")
    signups: int = Field(ge=0)
    premium_users: int = Field(ge=0)


class ContentValueScore(BaseModel):
    content_id: str
    title: str
    topic: str
    score: float
    components: dict[str, float]
    reach: int
    engagement: int
    signups: int
    premium_users: int
    signup_rate: float
    premium_rate: float


class TopicComparison(BaseModel):
    topic: str
    content_count: int
    total_reach: int
    total_signups: int
    total_premium_users: int
    avg_content_value_score: float
    signup_rate: float
    premium_rate: float


class ContentGapItem(BaseModel):
    content_id: str
    title: str
    topic: str
    reach: int
    signup_rate: float
    premium_rate: float
    content_value_score: float
    reason: str


class ContentValueWeights(BaseModel):
    """
    Weights for Content Value Score (must sum to 1.0).

    Defaults emphasize downstream value (signups / premium) over raw reach.
    """

    reach: float = Field(default=0.20, ge=0.0, le=1.0)
    engagement: float = Field(default=0.15, ge=0.0, le=1.0)
    signup_contribution: float = Field(default=0.30, ge=0.0, le=1.0)
    premium_conversion: float = Field(default=0.35, ge=0.0, le=1.0)

    def normalized(self) -> ContentValueWeights:
        total = self.reach + self.engagement + self.signup_contribution + self.premium_conversion
        if total <= 0:
            raise ValueError("Content value weights must sum to a positive number")
        return ContentValueWeights(
            reach=self.reach / total,
            engagement=self.engagement / total,
            signup_contribution=self.signup_contribution / total,
            premium_conversion=self.premium_conversion / total,
        )
