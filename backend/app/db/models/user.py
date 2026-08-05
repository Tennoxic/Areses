import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )


class UserSession(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )
