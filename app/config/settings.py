"""Environment-backed settings. Never hard-code secrets."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    youtube_max_pages: int = Field(default=10, alias="YOUTUBE_MAX_PAGES")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
