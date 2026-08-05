from pydantic import ConfigDict, Field

from app.schemas.base import CamelModel


class FolderCreate(CamelModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None


class OpmlImport(CamelModel):
    opml: str


class FolderOut(CamelModel):
    id: int
    name: str
    parent_id: int | None

    model_config = ConfigDict(from_attributes=True)


class FeedCreate(CamelModel):
    url: str = Field(max_length=2048)
    folder_id: int | None = None
    custom_name: str | None = Field(default=None, max_length=200)
    http_username: str | None = Field(default=None, max_length=200)
    http_password: str | None = Field(default=None, max_length=200)
    custom_headers: dict[str, str] | None = None


class FeedUpdate(CamelModel):
    folder_id: int | None = None
    custom_name: str | None = Field(default=None, max_length=200)
    fetch_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    summarize_enabled: bool | None = None
    http_username: str | None = Field(default=None, max_length=200)
    http_password: str | None = Field(default=None, max_length=200)
    custom_headers: dict[str, str] | None = None
    auto_read_pattern: str | None = Field(default=None, max_length=200)
    notify_enabled: bool | None = None
    hidden: bool | None = None


class BulkMove(CamelModel):
    subscription_ids: list[int]
    folder_id: int | None = None


class BulkDelete(CamelModel):
    subscription_ids: list[int]


class FeedPreviewRequest(CamelModel):
    url: str = Field(max_length=2048)
    http_username: str | None = Field(default=None, max_length=200)
    http_password: str | None = Field(default=None, max_length=200)


class FeedPreviewEntry(CamelModel):
    title: str
    link: str | None = None
    published: str | None = None


class FeedPreviewOut(CamelModel):
    feed_title: str | None
    resolved_url: str
    already_in_catalog: bool
    entries: list[FeedPreviewEntry]


class FeedOut(CamelModel):
    subscription_id: int
    source_id: int
    url: str
    site_url: str | None
    favicon_url: str | None
    custom_name: str | None
    folder_id: int | None
    fetch_interval_minutes: int
    summarize_enabled: bool
    is_broken: bool
    unread_count: int
    auto_read_pattern: str | None = None
    notify_enabled: bool = False
    hidden: bool = False
    last_error_message: str | None = None
    consecutive_fail_count: int = 0
    last_fetch_status: str | None = None
    already_in_catalog: bool = False
