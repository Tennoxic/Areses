import datetime

import pytest

from app.core.time import utcnow
from app.db.models import Source
from app.services import scheduler, source_service

_SAMPLE_FEED_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Sample Feed</title>
<link>https://example.test</link>
<item><title>Sample Article</title><link>https://example.test/a1</link></item>
</channel></rss>"""


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", headers: dict | None = None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("error", request=None, response=self)


def _make_fake_safe_get(behaviors: dict):
    async def _fake_safe_get(url, *args, **kwargs):
        behavior = behaviors.get(url)
        if behavior is None:
            raise AssertionError(f"unexpected url requested: {url}")
        if isinstance(behavior, Exception):
            raise behavior
        return behavior

    return _fake_safe_get


async def _create_source(db_session, url: str) -> Source:
    source = Source(url=url, next_fetch_at=utcnow())
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.mark.asyncio
async def test_failing_feed_does_not_affect_others(db_session, monkeypatch):
    good = await _create_source(db_session, "https://good.example.test/feed.xml")
    bad = await _create_source(db_session, "https://bad.example.test/feed.xml")

    import httpx

    behaviors = {
        good.url: _FakeResponse(200, _SAMPLE_FEED_XML),
        bad.url: httpx.ConnectError("connection refused"),
    }
    monkeypatch.setattr(
        "app.services.scheduler.net_guard.safe_get", _make_fake_safe_get(behaviors)
    )

    async def _fake_extract(url, auth):
        return "some extracted plain text content " * 20

    monkeypatch.setattr(scheduler, "extract_article_content", _fake_extract)

    await scheduler.fetch_single_feed(bad.id)
    await scheduler.fetch_single_feed(good.id)

    await db_session.refresh(bad)
    await db_session.refresh(good)

    assert bad.consecutive_fail_count == 1
    assert bad.last_fetch_status == "error"
    assert good.consecutive_fail_count == 0
    assert good.last_fetch_status == "ok"


@pytest.mark.asyncio
async def test_not_modified_response_does_not_touch_content(db_session, monkeypatch):
    source = await _create_source(db_session, "https://notmodified.example.test/feed.xml")

    behaviors = {source.url: _FakeResponse(304)}
    monkeypatch.setattr(
        "app.services.scheduler.net_guard.safe_get", _make_fake_safe_get(behaviors)
    )

    await scheduler.fetch_single_feed(source.id)
    await db_session.refresh(source)

    assert source.last_fetch_status == "not_modified"
    assert source.consecutive_fail_count == 0


@pytest.mark.asyncio
async def test_fetch_lock_prevents_double_scan(db_session):
    source = await _create_source(db_session, "https://lock.example.test/feed.xml")

    first_acquire = await source_service.acquire_fetch_lock(db_session, source.id)
    second_acquire = await source_service.acquire_fetch_lock(db_session, source.id)

    assert first_acquire is True
    assert second_acquire is False

    await source_service.release_fetch_lock(db_session, source.id)
    third_acquire = await source_service.acquire_fetch_lock(db_session, source.id)
    assert third_acquire is True


@pytest.mark.asyncio
async def test_due_sources_respects_active_and_lock_and_schedule(db_session):
    now = utcnow()

    due = Source(url="https://due.example.test/feed.xml", next_fetch_at=now - datetime.timedelta(minutes=1))
    not_due = Source(url="https://notdue.example.test/feed.xml", next_fetch_at=now + datetime.timedelta(hours=1))
    inactive = Source(
        url="https://inactive.example.test/feed.xml",
        next_fetch_at=now - datetime.timedelta(minutes=1),
        active=False,
    )
    locked = Source(
        url="https://locked.example.test/feed.xml",
        next_fetch_at=now - datetime.timedelta(minutes=1),
        is_fetching=True,
    )
    db_session.add_all([due, not_due, inactive, locked])
    await db_session.commit()

    due_sources = await source_service.due_sources(db_session)
    due_urls = {s.url for s in due_sources}

    assert due.url in due_urls
    assert not_due.url not in due_urls
    assert inactive.url not in due_urls
    assert locked.url not in due_urls
