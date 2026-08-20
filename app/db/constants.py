"""Shared domain vocabulary for acquisition and content."""

from enum import StrEnum


class Channel(StrEnum):
    YOUTUBE = "YouTube"
    ORGANIC_SEARCH = "Organic Search"
    LINKEDIN = "LinkedIn"
    INSTAGRAM = "Instagram"
    PAID = "Paid"
    DIRECT = "Direct"


class Topic(StrEnum):
    ETFS = "ETFs"
    STOCKS = "Stocks"
    CRYPTO = "Crypto"
    PERSONAL_FINANCE = "Personal Finance"
    REAL_ESTATE = "Real Estate"
    BUDGETING = "Budgeting"


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


FUNNEL_STAGES: tuple[str, ...] = (
    "views",
    "visits",
    "signups",
    "activated_users",
    "premium_users",
)

DATASET_LABEL = "synthetic_v1"
