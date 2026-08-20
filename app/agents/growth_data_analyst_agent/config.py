"""Agent configuration (no secrets)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DataAnalystConfig:
    default_days: int = 30
    max_claims: int = 12
