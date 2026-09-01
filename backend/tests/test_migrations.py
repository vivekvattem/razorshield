from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config


def config_for(database_url: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_upgrade_downgrade_and_reupgrade(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = config_for(database_url)
    engine = create_engine(database_url)
    expected = {"merchants", "customers", "orders", "return_requests", "risk_assessments", "audit_events"}
    try:
        command.upgrade(config, "head")
        assert expected.issubset(inspect(engine).get_table_names())
        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]
        command.upgrade(config, "head")
        assert expected.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
