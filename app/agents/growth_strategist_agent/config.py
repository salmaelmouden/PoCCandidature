"""Config for growth_strategist_agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StrategistConfig(BaseModel):
    max_recommendations: int = Field(default=3, ge=1, le=5)
