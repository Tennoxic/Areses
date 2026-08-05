import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.models.base import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (Index("ix_sources_next_fetch_at", "next_fetch_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    site_url: Mapped[str | None] = mapped_column(String, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String, nullable=True)
    fetch_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=60, server_default="60"
    )
    http_username: Mapped[str | None] = mapped_column(String, nullable=True)
    http_password: Mapped[str | None] = mapped_column(String, nullable=True)
    custom_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String, nullable=True)
    last_fetched_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    next_fetch_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )
    last_fetch_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_fail_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    backoff_multiplier: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    is_fetching: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )
