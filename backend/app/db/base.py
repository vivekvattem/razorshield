from __future__ import annotations

<<<<<<< HEAD
from datetime import UTC, datetime
=======
from datetime import datetime, timezone
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
<<<<<<< HEAD
    return datetime.now(UTC)
=======
    return datetime.now(timezone.utc)
>>>>>>> 58e2af2715e314de060b741992c07c170726891e


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
<<<<<<< HEAD
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
=======
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
