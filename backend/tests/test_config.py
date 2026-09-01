from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_postgres_and_secret() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(environment="production", database_url="sqlite:///unsafe.db")


def test_wildcard_credentials_are_rejected() -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(cors_origins=["*"], cors_allow_credentials=True)


def test_valid_production_settings() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://user:pass@localhost/db",
        secret_key="a" * 32,
    )
    assert settings.environment == "production"
