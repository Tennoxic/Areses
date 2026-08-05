import datetime
import re

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.db.models import Article, Source
from app.services.sanitizer import sanitize_plain_text, strip_tags

_FAVICON_TIMEOUT = 10.0


async def due_sources(session: AsyncSession) -> list[Source]:
    now = utcnow()
    result = await session.execute(
        select(Source).where(
            Source.active.is_(True),
            Source.next_fetch_at <= now,
            Source.is_fetching.is_(False),
        )
    )
    return list(result.scalars().all())


async def acquire_fetch_lock(session: AsyncSession, source_id: int) -> bool:
    result = await session.execute(
        update(Source)
        .where(Source.id == source_id, Source.is_fetching.is_(False))
        .values(is_fetching=True)
    )
    await session.commit()
    return result.rowcount > 0


async def release_fetch_lock(session: AsyncSession, source_id: int) -> None:
    await session.execute(
        update(Source).where(Source.id == source_id).values(is_fetching=False)
    )
    await session.commit()


async def article_exists(session: AsyncSession, url: str) -> bool:
    result = await session.execute(select(Article.id).where(Article.url == url))
    return result.scalar_one_or_none() is not None


async def save_article(
    session: AsyncSession,
    source_id: int,
    url: str,
    title: str,
    content: str | None,
    published_at: datetime.datetime | None,
    author: str | None = None,
    enclosure_url: str | None = None,
    enclosure_type: str | None = None,
) -> Article:
    plain_text = strip_tags(content) if content else ""
    word_count = len(plain_text.split()) if plain_text else None
    reading_time_minutes = max(1, round(word_count / 200)) if word_count else None
    safe_title = sanitize_plain_text(title) or "(untitled)"
    safe_author = sanitize_plain_text(author) if author else None
    article = Article(
        source_id=source_id,
        url=url,
        title=safe_title,
        author=safe_author,
        content=content,
        word_count=word_count,
        reading_time_minutes=reading_time_minutes,
        published_at=published_at,
        enclosure_url=enclosure_url,
        enclosure_type=enclosure_type,
        extraction_failed=content is None,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return article


_ICON_LINK_PATTERN = re.compile(
    r'<link[^>]+rel=["\'](?:shortcut icon|icon|apple-touch-icon)["\'][^>]*>',
    re.IGNORECASE,
)


def _discover_icon_href(html: str) -> str | None:
    best_match = None
    for match in _ICON_LINK_PATTERN.finditer(html):
        best_match = match.group(0)
        if "apple-touch-icon" not in best_match.lower():
            break
    if not best_match:
        return None
    href_match = re.search(r'href=["\']([^"\']+)["\']', best_match)
    return href_match.group(1) if href_match else None


async def fetch_favicon(session: AsyncSession, source_id: int, site_url: str) -> None:
    from urllib.parse import urljoin

    from app.services.net_guard import safe_get

    favicon_url: str | None = None
    try:
        page_response = await safe_get(site_url, timeout=_FAVICON_TIMEOUT)
        if page_response.status_code == 200:
            href = _discover_icon_href(page_response.text)
            if href:
                favicon_url = urljoin(site_url, href)

        if favicon_url is None:
            fallback_url = f"{site_url.rstrip('/')}/favicon.ico"
            fallback_response = await safe_get(fallback_url, timeout=_FAVICON_TIMEOUT)
            if fallback_response.status_code == 200:
                favicon_url = fallback_url
    except Exception:
        favicon_url = None

    if favicon_url:
        await session.execute(
            update(Source).where(Source.id == source_id).values(favicon_url=favicon_url)
        )
        await session.commit()
