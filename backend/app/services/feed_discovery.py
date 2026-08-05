import re
from urllib.parse import urljoin

import feedparser
import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.db.models import Source
from app.services.net_guard import safe_get

_ALTERNATE_LINK_PATTERN = re.compile(
    r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>',
    re.IGNORECASE,
)
_ALTERNATE_LINK_PATTERN_SWAPPED = re.compile(
    r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+rel=["\']alternate["\'][^>]*>',
    re.IGNORECASE,
)
_HREF_PATTERN = re.compile(r'href=["\']([^"\']+)["\']')


async def _fetch_text(url: str, auth: tuple[str, str] | None) -> str:
    response = await safe_get(url, auth=auth, timeout=15.0)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "fetch_failed",
                "message": f"could not fetch URL: HTTP {exc.response.status_code}",
            },
        ) from exc
    return response.text


def _find_linked_feed_url(url: str, html_text: str) -> str:
    match = _ALTERNATE_LINK_PATTERN.search(html_text)
    if not match:
        match = _ALTERNATE_LINK_PATTERN_SWAPPED.search(html_text)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "feed_not_found",
                "message": "no RSS/Atom feed found at or linked from this URL",
            },
        )

    href_match = _HREF_PATTERN.search(match.group(0))
    if not href_match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "feed_not_found",
                "message": "no RSS/Atom feed found at or linked from this URL",
            },
        )

    return urljoin(url, href_match.group(1))


async def discover_feed_url(url: str, auth: tuple[str, str] | None = None) -> str:
    text = await _fetch_text(url, auth)
    if feedparser.parse(text).get("version"):
        return url
    return _find_linked_feed_url(url, text)


async def discover_and_fetch(
    url: str, auth: tuple[str, str] | None = None
) -> tuple[str, feedparser.FeedParserDict]:
    text = await _fetch_text(url, auth)
    parsed = feedparser.parse(text)
    if parsed.get("version"):
        return url, parsed

    resolved_url = _find_linked_feed_url(url, text)
    resolved_text = await _fetch_text(resolved_url, auth)
    return resolved_url, feedparser.parse(resolved_text)


async def _create_source(session: AsyncSession, url: str) -> Source:
    source = Source(url=url, next_fetch_at=utcnow())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


async def get_or_create_source_by_url(session: AsyncSession, url: str) -> Source:
    result = await session.execute(select(Source).where(Source.url == url))
    source = result.scalar_one_or_none()
    if source is not None:
        return source
    return await _create_source(session, url)


async def get_or_create_source(
    session: AsyncSession, url: str, auth: tuple[str, str] | None = None
) -> tuple[Source, bool]:
    result = await session.execute(select(Source).where(Source.url == url))
    source = result.scalar_one_or_none()
    if source is not None:
        return source, False

    resolved_url = await discover_feed_url(url, auth)
    result = await session.execute(select(Source).where(Source.url == resolved_url))
    source = result.scalar_one_or_none()
    if source is not None:
        return source, False

    source = await _create_source(session, resolved_url)
    return source, True
