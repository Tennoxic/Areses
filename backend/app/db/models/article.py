import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.models.base import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (Index("ix_articles_source_id_fetched_at", "source_id", "fetched_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_pending: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    enclosure_url: Mapped[str | None] = mapped_column(String, nullable=True)
    enclosure_type: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_failed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    published_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    fetched_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )


class UserArticleState(Base):
    __tablename__ = "user_article_state"
    __table_args__ = (
        Index(
            "ix_user_article_state_user_id_is_read_article_id",
            "user_id",
            "is_read",
            "article_id",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id"), primary_key=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    starred: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    read_later: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    scroll_position: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0"
    )
