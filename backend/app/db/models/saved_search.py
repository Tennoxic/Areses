from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    query: Mapped[str] = mapped_column(String, nullable=False)
