import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.models.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id"), nullable=True
    )
    custom_name: Mapped[str | None] = mapped_column(String, nullable=True)
    summarize_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    auto_read_pattern: Mapped[str | None] = mapped_column(String, nullable=True)
    notify_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    hidden: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    fetch_interval_minutes_override: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id"), nullable=True
    )
