import asyncio
import datetime
import json
import logging

import feedparser
from sqlalchemy import select

from app.core.crypto import decrypt_secret
from app.core.regex_safety import safe_search
from app.core.time import utcnow
from app.db.models import Subscription
from app.db.session import async_session_maker
from app.services import ai_summary, net_guard, push_service, source_service
from app.services.events import NewArticleEvent, broadcaster
from app.services.extraction.extractor import extract_article_content
from app.services.sanitizer import sanitize_html

_logger = logging.getLogger(__name__)

_TICK_SECONDS = 60
_BETWEEN_FEEDS_SECONDS = 0.5
_USER_AGENT = "ARESES/0.1 (+https://github.com/areses)"
_MAX_BACKOFF_MULTIPLIER = 24

_running = False


def _extract_enclosure(entry) -> tuple[str | None, str | None]:
    enclosures = entry.get("enclosures") or entry.get("links") or []
    for link in enclosures:
        link_type = (link.get("type") or "").lower()
        rel = (link.get("rel") or "").lower()
        if rel == "enclosure" or link_type.startswith(("audio/", "video/")):
            href = link.get("href") or link.get("url")
            if href:
                return href, link.get("type")
    return None, None


async def _apply_auto_read_rules(session, source_id: int, article) -> None:
    from app.db.models import Subscription, UserArticleState

    result = await session.execute(
        select(Subscription).where(
            Subscription.source_id == source_id,
            Subscription.auto_read_pattern.is_not(None),
        )
    )
    for sub in result.scalars().all():
        if not sub.auto_read_pattern:
            continue
        if safe_search(sub.auto_read_pattern, article.title):
            session.add(
                UserArticleState(
                    user_id=sub.user_id,
                    article_id=article.id,
                    is_read=True,
                    read_at=utcnow(),
                )
            )
    await session.commit()


async def _notify_subscribers(session, source_id: int, article) -> None:
    result = await session.execute(
        select(Subscription.user_id).where(
            Subscription.source_id == source_id,
            Subscription.notify_enabled.is_(True),
        )
    )
    for (user_id,) in result.all():
        await push_service.notify_user(
            session,
            user_id,
            title=article.title,
            body="New article",
            url=f"/?article={article.id}",
        )


async def _effective_interval_minutes(session, source) -> int:
    result = await session.execute(
        select(Subscription.fetch_interval_minutes_override).where(
            Subscription.source_id == source.id,
            Subscription.fetch_interval_minutes_override.is_not(None),
        )
    )
    overrides = [row[0] for row in result.all()]
    if overrides:
        return min(overrides)
    return source.fetch_interval_minutes


def _feed_provided_content(entry) -> str | None:
    content_list = entry.get("content")
    if content_list:
        value = content_list[0].get("value")
        if value and value.strip():
            return sanitize_html(value)
    summary = entry.get("summary")
    if summary and summary.strip():
        return sanitize_html(summary)
    return None


async def fetch_single_feed(source_id: int) -> None:
    async with async_session_maker() as session:
        source = await session.get(source_service.Source, source_id)
        if source is None:
            return

        headers = {"User-Agent": _USER_AGENT}
        if source.etag:
            headers["If-None-Match"] = source.etag
        if source.last_modified:
            headers["If-Modified-Since"] = source.last_modified
        if source.custom_headers:
            try:
                headers.update(json.loads(source.custom_headers))
            except (json.JSONDecodeError, TypeError):
                pass
        auth = None
        if source.http_username:
            auth = (source.http_username, decrypt_secret(source.http_password) or "")

        now = utcnow()
        base_interval = datetime.timedelta(
            minutes=await _effective_interval_minutes(session, source)
        )
        was_failing = source.consecutive_fail_count > 0
        first_scan = source.last_fetched_at is None

        try:
            response = await net_guard.safe_get(
                source.url, auth=auth, timeout=20.0, headers=headers
            )

            if response.status_code == 304:
                source.last_fetch_status = "not_modified"
                source.consecutive_fail_count = 0
                source.backoff_multiplier = 1
                source.last_error_message = None
                source.next_fetch_at = now + base_interval
                source.last_fetched_at = now
                await session.commit()
                return

            response.raise_for_status()

            parsed = feedparser.parse(response.text)
            source.etag = response.headers.get("ETag")
            source.last_modified = response.headers.get("Last-Modified")
            source.last_fetch_status = "ok"
            source.consecutive_fail_count = 0
            source.backoff_multiplier = 1
            source.last_error_message = None
            source.next_fetch_at = now + base_interval
            source.last_fetched_at = now
            if not source.site_url and parsed.feed.get("link"):
                source.site_url = parsed.feed.get("link")
            await session.commit()

            source_id_val = source.id
            for entry in parsed.entries:
                article_url = entry.get("link")
                if not article_url:
                    continue
                try:
                    if await source_service.article_exists(session, article_url):
                        continue
                    content = await extract_article_content(article_url, auth)
                    if not content:
                        content = _feed_provided_content(entry)
                    enclosure_url, enclosure_type = _extract_enclosure(entry)
                    if not content and not enclosure_url:
                        continue
                    published_at = None
                    if entry.get("published_parsed"):
                        published_at = datetime.datetime(*entry.published_parsed[:6])
                    article = await source_service.save_article(
                        session,
                        source_id=source_id_val,
                        url=article_url,
                        title=entry.get("title", "(untitled)"),
                        content=content,
                        published_at=published_at,
                        author=entry.get("author"),
                        enclosure_url=enclosure_url,
                        enclosure_type=enclosure_type,
                    )
                    await ai_summary.maybe_enqueue_summary(session, article)
                    await _apply_auto_read_rules(session, source_id_val, article)
                    await _notify_subscribers(session, source_id_val, article)
                    subscriber_ids_result = await session.execute(
                        select(Subscription.user_id).where(
                            Subscription.source_id == source_id_val
                        )
                    )
                    subscriber_user_ids = [row[0] for row in subscriber_ids_result.all()]
                    await broadcaster.publish(
                        "newArticle",
                        NewArticleEvent(
                            article_id=article.id,
                            source_id=source_id_val,
                            title=article.title,
                        ).model_dump(by_alias=True),
                        subscriber_user_ids,
                    )
                except Exception:
                    _logger.exception(
                        "failed to process feed entry for source %s", source_id_val
                    )
                    await session.rollback()
                    continue

            source = await session.get(source_service.Source, source_id_val)
            if source is not None and (
                (was_failing and source.consecutive_fail_count == 0) or first_scan
            ):
                if source.site_url:
                    await source_service.fetch_favicon(session, source.id, source.site_url)

        except Exception as exc:
            if source is not None:
                source.consecutive_fail_count += 1
                source.backoff_multiplier = min(
                    source.backoff_multiplier * 2, _MAX_BACKOFF_MULTIPLIER
                )
                source.last_fetch_status = "error"
                source.last_error_message = str(exc)[:500]
                source.next_fetch_at = now + (base_interval * source.backoff_multiplier)
                source.last_fetched_at = now
                await session.commit()


async def _run_tick() -> None:
    async with async_session_maker() as session:
        due = await source_service.due_sources(session)

    for source in due:
        async with async_session_maker() as lock_session:
            acquired = await source_service.acquire_fetch_lock(lock_session, source.id)
        if not acquired:
            continue
        try:
            await fetch_single_feed(source.id)
        finally:
            async with async_session_maker() as lock_session:
                await source_service.release_fetch_lock(lock_session, source.id)
        await asyncio.sleep(_BETWEEN_FEEDS_SECONDS)

    async with async_session_maker() as session:
        await ai_summary.process_pending_summaries(session)


async def run_forever() -> None:
    global _running
    _running = True
    last_retention_run: datetime.date | None = None
    last_backup_run: datetime.date | None = None
    while _running:
        try:
            await _run_tick()

            today = utcnow().date()
            if last_retention_run != today:
                from app.services import read_state

                async with async_session_maker() as session:
                    await read_state.run_retention_cleanup(session)
                last_retention_run = today

            if last_backup_run != today:
                from app.services import backup_service

                async with async_session_maker() as session:
                    await backup_service.maybe_run_scheduled_backup(session)
                last_backup_run = today
        except Exception:
            _logger.exception("scheduler tick failed (retention/backup step)")

        await asyncio.sleep(_TICK_SECONDS)


def stop() -> None:
    global _running
    _running = False


async def trigger_fetch_now(source_id: int) -> None:
    async with async_session_maker() as session:
        acquired = await source_service.acquire_fetch_lock(session, source_id)
    if not acquired:
        return
    try:
        await fetch_single_feed(source_id)
    finally:
        async with async_session_maker() as session:
            await source_service.release_fetch_lock(session, source_id)
