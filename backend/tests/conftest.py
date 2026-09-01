from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app


def upgrade_database(database_url: str) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def database(database_url: str) -> Database:
    upgrade_database(database_url)
    instance = Database(database_url)
    yield instance
    instance.engine.dispose()


@pytest.fixture
def session(database: Database) -> Generator[Session, None, None]:
    current = database.session_factory()
    try:
        yield current
    finally:
        current.close()


@pytest.fixture
def app(database_url: str):
    upgrade_database(database_url)
    return create_app(
        Settings(
            environment="test",
            database_url=database_url,
            cors_origins=["http://testserver"],
            log_level="WARNING",
        )
    )


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
