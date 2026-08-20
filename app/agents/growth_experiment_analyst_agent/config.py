"""Config for growth_experiment_analyst_agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExperimentAnalystConfig(BaseModel):
    default_experiment_key: str = "syn_exp_youtube_cta"
    alpha: float = Field(default=0.05, gt=0.0, lt=0.5)
