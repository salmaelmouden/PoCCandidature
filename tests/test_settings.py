"""Tests for settings normalisation — the bits that only bite in deployment."""

from __future__ import annotations

import pytest

from app.config.settings import Settings, normalize_database_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Managed providers (Railway, Render, Neon, Heroku) hand out these two.
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        # Already correct — left alone.
        ("postgresql+psycopg://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        # An explicitly requested driver is respected, not overridden.
        ("postgresql+asyncpg://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        # Non-postgres URLs pass through untouched.
        ("sqlite+pysqlite:///:memory:", "sqlite+pysqlite:///:memory:"),
    ],
)
def test_database_url_forces_psycopg3(given: str, expected: str) -> None:
    assert normalize_database_url(given) == expected


def test_credentials_and_query_string_survive_rewrite() -> None:
    given = "postgresql://user:p%40ss@host.internal:5432/rail?sslmode=require"

    result = normalize_database_url(given)

    assert result == "postgresql+psycopg://user:p%40ss@host.internal:5432/rail?sslmode=require"


def test_settings_applies_normalisation() -> None:
    settings = Settings(DATABASE_URL="postgres://u:p@h:5432/db")

    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")


def test_settings_builds_url_from_parts_when_database_url_absent() -> None:
    settings = Settings(
        DATABASE_URL="",
        POSTGRES_USER="growth",
        POSTGRES_PASSWORD="growth",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5434,
        POSTGRES_DB="growth_intelligence",
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+psycopg://growth:growth@localhost:5434/growth_intelligence"
    )


def test_blank_placeholders_are_treated_as_unset() -> None:
    settings = Settings(ANTHROPIC_API_KEY="", YOUTUBE_API_KEY="  ", CA_BUNDLE_PATH="")

    assert settings.anthropic_api_key is None
    assert settings.youtube_api_key is None
    assert settings.ca_bundle_path is None


def test_blank_model_falls_back_to_default() -> None:
    """`LLM_MODEL=` in .env must not be sent to the API as the model name."""
    assert Settings(LLM_MODEL="").llm_model == "claude-opus-5"
    assert Settings(LLM_MODEL="claude-sonnet-5").llm_model == "claude-sonnet-5"
