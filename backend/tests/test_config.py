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
        cors_origins=["https://razorshield.example"],
    )
    assert settings.environment == "production"


def test_render_postgres_url_is_normalized() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql://user:pass@db.example/razorshield",
        secret_key="a" * 32,
        cors_origins=["https://razorshield.vercel.app"],
    )
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_production_rejects_wildcard_or_insecure_cors() -> None:
    for origins in (["*"], ["http://localhost:5173"]):
        with pytest.raises(ValidationError, match="CORS"):
            Settings(
                environment="production",
                database_url="postgresql://user:pass@db.example/razorshield",
                secret_key="a" * 32,
                cors_origins=origins,
            )
