import datetime
from typing import Literal

from app.schemas.base import CamelModel


class ArticleOut(CamelModel):
    id: int
    source_id: int
    url: str
    title: str
    ai_summary: str | None
    word_count: int | None
    reading_time_minutes: int | None
    published_at: datetime.datetime | None
    fetched_at: datetime.datetime
    is_read: bool
    starred: bool
    read_later: bool
    scroll_position: float
    enclosure_url: str | None = None
    enclosure_type: str | None = None
    extraction_failed: bool = False


class ArticleDetailOut(ArticleOut):
    content: str | None = None


class ScrollPositionUpdate(CamelModel):
    position: float


class MarkAllReadRequest(CamelModel):
    source_id: int | None = None
    folder_id: int | None = None


class StarToggleOut(CamelModel):
    starred: bool


class ReadLaterToggleOut(CamelModel):
    read_later: bool


class TranslateRequest(CamelModel):
    target_language: Literal[
        "Turkish",
        "English",
        "Spanish",
        "German",
        "French",
        "Portuguese",
        "Italian",
        "Russian",
        "Arabic",
        "Japanese",
    ]


class TranslateOut(CamelModel):
    translated_content: str
