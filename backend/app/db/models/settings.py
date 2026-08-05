from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class Setting(Base):
    __tablename__ = "settings"

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), primary_key=True, nullable=True
    )
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
