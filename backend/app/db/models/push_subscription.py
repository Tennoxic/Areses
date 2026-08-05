import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.models.base import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("endpoint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(String, nullable=False)
    auth: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=utcnow
    )
