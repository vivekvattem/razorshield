from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

<<<<<<< HEAD
from sqlalchemy import create_engine, event, text
=======
from sqlalchemy import create_engine, text
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
<<<<<<< HEAD
        if database_url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

=======
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

>>>>>>> 58e2af2715e314de060b741992c07c170726891e
    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency, overridden by the application factory at startup."""
    raise RuntimeError("Database dependency is not configured")
