"""Environment-backed settings. Never hard-code secrets."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingDatabaseUrlError(RuntimeError):
    """Raised when a production deploy has no database configured."""


def normalize_database_url(url: str) -> str:
    """
    Force the psycopg (v3) driver on a provider-supplied connection string.

    Managed Postgres providers hand out `postgres://` or `postgresql://`.
    SQLAlchemy maps both to **psycopg2**, which this project does not install —
    the app would fail at first connection with `ModuleNotFoundError: psycopg2`.
    Only the scheme is rewritten; credentials and query string are untouched.
    """
    for prefix in ("postgresql+psycopg://", "postgresql+", "postgres+"):
        if url.startswith(prefix):
            return url  # an explicit driver was requested — respect it
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5434, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="growth_intelligence", alias="POSTGRES_DB")
    postgres_user: str = Field(default="growth", alias="POSTGRES_USER")
    postgres_password: str = Field(default="growth", alias="POSTGRES_PASSWORD")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    synthetic_seed: int = Field(default=42, alias="SYNTHETIC_SEED")
    synthetic_days: int = Field(default=90, alias="SYNTHETIC_DAYS")

    youtube_api_key: str | None = Field(default=None, alias="YOUTUBE_API_KEY")
    youtube_channel_id: str | None = Field(default=None, alias="YOUTUBE_CHANNEL_ID")
    youtube_timeout_seconds: float = Field(default=30.0, alias="YOUTUBE_TIMEOUT_SECONDS")
    youtube_max_retries: int = Field(default=3, alias="YOUTUBE_MAX_RETRIES")
    youtube_max_pages: int = Field(default=2, alias="YOUTUBE_MAX_PAGES")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-opus-5", alias="LLM_MODEL")
    llm_batch_size: int = Field(default=40, alias="LLM_BATCH_SIZE")
    # Corporate TLS interception (e.g. Zscaler) breaks Python's certifi bundle while
    # curl still works. Point this at the system CA bundle when that happens.
    ca_bundle_path: str | None = Field(default=None, alias="CA_BUNDLE_PATH")

    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str | None = Field(default=None, alias="LANGFUSE_HOST")

    @field_validator(
        "anthropic_api_key",
        "youtube_api_key",
        "youtube_channel_id",
        "ca_bundle_path",
        "langfuse_public_key",
        "langfuse_secret_key",
        "langfuse_host",
        "database_url",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        """`.env` placeholders are empty strings — treat them as unset, not as a value."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("llm_model", mode="before")
    @classmethod
    def _blank_to_default(cls, value: object) -> object:
        """An empty `LLM_MODEL=` must not silently override the default model."""
        if isinstance(value, str) and not value.strip():
            return "claude-opus-5"
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return normalize_database_url(self.database_url)
        if self.app_env.lower() in {"production", "prod"}:
            # Falling back to the local-dev default in production produces a
            # "connection refused to 127.0.0.1:5434" buried in a healthcheck
            # timeout. Say what is actually missing instead.
            raise MissingDatabaseUrlError(
                "DATABASE_URL is not set and APP_ENV is production. Managed hosts do "
                "not inject it automatically — on Railway add an explicit reference: "
                "DATABASE_URL=${{Postgres.DATABASE_URL}} (use your Postgres service's "
                "name). Refusing to fall back to "
                f"{self.postgres_host}:{self.postgres_port}."
            )
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
