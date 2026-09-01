from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration; secrets are supplied only through the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RazorShield"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./razorshield.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cors_allow_credentials: bool = False
    secret_key: str | None = None
    log_level: str = "INFO"

    @field_validator("cors_origins")
    @classmethod
    def reject_blank_origins(cls, value: list[str]) -> list[str]:
        if any(not origin.strip() for origin in value):
            raise ValueError("CORS origins must not contain blank values")
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.cors_allow_credentials and "*" in self.cors_origins:
            raise ValueError("wildcard CORS origins cannot be used with credentials")
        if self.environment == "production":
            if self.database_url.startswith("sqlite"):
                raise ValueError("production requires a PostgreSQL database URL")
            if not self.secret_key or len(self.secret_key) < 32:
                raise ValueError("production requires a secret key of at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
