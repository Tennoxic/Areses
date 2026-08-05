import json
import re
import xml.etree.ElementTree as ET

import defusedxml.ElementTree as DefusedET
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.core.crypto import encrypt_secret
from app.core.regex_safety import is_unsafe_pattern
from app.db.models import Article, Folder, Source, Subscription, User, UserArticleState
from app.db.session import get_session
from app.schemas.feeds import (
    BulkDelete,
    BulkMove,
    FeedCreate,
    FeedOut,
    FeedPreviewEntry,
    FeedPreviewOut,
    FeedPreviewRequest,
    FeedUpdate,
    OpmlImport,
)
from app.services import feed_discovery, read_state, scheduler

router = APIRouter(prefix="/api", tags=["feeds"])

_BROKEN_THRESHOLD = 5


@router.post("/feeds", response_model=FeedOut)
async def create_feed(
    body: FeedCreate,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    auth = (body.http_username, body.http_password or "") if body.http_username else None
    source, is_new = await feed_discovery.get_or_create_source(session, body.url, auth)
    if is_new:
        if body.http_username:
            source.http_username = body.http_username
        if body.http_password:
            source.http_password = encrypt_secret(body.http_password)
        if body.custom_headers:
            source.custom_headers = json.dumps(body.custom_headers)
        await session.commit()

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.source_id == source.id
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "already_subscribed", "message": "already subscribed"},
        )

    subscription = Subscription(
        user_id=user.id,
        source_id=source.id,
        folder_id=body.folder_id,
        custom_name=body.custom_name,
    )
    source.active = True
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return {
        "subscription_id": subscription.id,
        "source_id": source.id,
        "url": source.url,
        "site_url": source.site_url,
        "favicon_url": source.favicon_url,
        "custom_name": subscription.custom_name,
        "folder_id": subscription.folder_id,
        "fetch_interval_minutes": subscription.fetch_interval_minutes_override or source.fetch_interval_minutes,
        "summarize_enabled": subscription.summarize_enabled,
        "is_broken": source.consecutive_fail_count >= _BROKEN_THRESHOLD,
        "unread_count": 0,
        "auto_read_pattern": subscription.auto_read_pattern,
        "notify_enabled": subscription.notify_enabled,
        "hidden": subscription.hidden,
        "last_error_message": source.last_error_message,
        "consecutive_fail_count": source.consecutive_fail_count,
        "last_fetch_status": source.last_fetch_status,
        "already_in_catalog": not is_new,
    }


@router.get("/feeds", response_model=list[FeedOut])
async def list_feeds(
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        select(Subscription, Source)
        .join(Source, Source.id == Subscription.source_id)
        .where(Subscription.user_id == user.id)
    )
    rows = result.all()
    unread_counts = await read_state.get_unread_counts(session, user.id)

    return [
        {
            "subscription_id": sub.id,
            "source_id": source.id,
            "url": source.url,
            "site_url": source.site_url,
            "favicon_url": source.favicon_url,
            "custom_name": sub.custom_name,
            "folder_id": sub.folder_id,
            "fetch_interval_minutes": sub.fetch_interval_minutes_override or source.fetch_interval_minutes,
            "summarize_enabled": sub.summarize_enabled,
            "is_broken": source.consecutive_fail_count >= _BROKEN_THRESHOLD,
            "unread_count": unread_counts.get(source.id, 0),
            "auto_read_pattern": sub.auto_read_pattern,
            "notify_enabled": sub.notify_enabled,
            "hidden": sub.hidden,
            "last_error_message": source.last_error_message,
            "consecutive_fail_count": source.consecutive_fail_count,
            "last_fetch_status": source.last_fetch_status,
        }
        for sub, source in rows
    ]


@router.patch("/feeds/{subscription_id}")
async def update_feed(
    subscription_id: int,
    body: FeedUpdate,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Subscription).where(
            Subscription.id == subscription_id, Subscription.user_id == user.id
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if body.folder_id is not None:
        subscription.folder_id = body.folder_id
    if body.custom_name is not None:
        subscription.custom_name = body.custom_name
    if body.summarize_enabled is not None:
        subscription.summarize_enabled = body.summarize_enabled
    if body.auto_read_pattern is not None:
        if body.auto_read_pattern:
            try:
                re.compile(body.auto_read_pattern)
            except re.error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "invalid_regex",
                        "message": "invalid regular expression",
                    },
                )
            if is_unsafe_pattern(body.auto_read_pattern):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "unsafe_regex_pattern",
                        "message": "pattern is too long or has a catastrophic-backtracking shape",
                    },
                )
        subscription.auto_read_pattern = body.auto_read_pattern or None
    if body.notify_enabled is not None:
        subscription.notify_enabled = body.notify_enabled
    if body.hidden is not None:
        subscription.hidden = body.hidden

    if body.fetch_interval_minutes is not None:
        subscription.fetch_interval_minutes_override = body.fetch_interval_minutes

    if body.http_username is not None or body.http_password is not None or body.custom_headers is not None:
        source_result = await session.execute(
            select(Source).where(Source.id == subscription.source_id)
        )
        source = source_result.scalar_one()
        if body.http_username is not None:
            source.http_username = body.http_username or None
        if body.http_password is not None:
            source.http_password = encrypt_secret(body.http_password) or None
        if body.custom_headers is not None:
            source.custom_headers = json.dumps(body.custom_headers) if body.custom_headers else None

    await session.commit()
    return {"status": "ok"}


@router.delete("/feeds/{subscription_id}")
async def delete_feed(
    subscription_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Subscription).where(
            Subscription.id == subscription_id, Subscription.user_id == user.id
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    source_id = subscription.source_id
    await session.execute(
        delete(UserArticleState).where(
            UserArticleState.user_id == user.id,
            UserArticleState.article_id.in_(select(Article.id).where(Article.source_id == source_id)),
        )
    )
    await session.delete(subscription)
    await session.commit()

    remaining = await session.execute(
        select(Subscription.id).where(Subscription.source_id == source_id)
    )
    if remaining.first() is None:
        source_result = await session.execute(
            select(Source).where(Source.id == source_id)
        )
        source = source_result.scalar_one()
        source.active = False
        await session.commit()

    return {"status": "ok"}


@router.post("/feeds/{subscription_id}/refresh")
async def refresh_feed(
    subscription_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Subscription).where(
            Subscription.id == subscription_id, Subscription.user_id == user.id
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await scheduler.trigger_fetch_now(subscription.source_id)
    return {"status": "ok"}


@router.post("/feeds/import-opml")
async def import_opml(
    body: OpmlImport,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    root = DefusedET.fromstring(body.opml)
    imported = 0

    async def process(element: ET.Element, folder_id: int | None) -> None:
        nonlocal imported
        for outline in element.findall("outline"):
            xml_url = outline.get("xmlUrl")
            if xml_url:
                source = await feed_discovery.get_or_create_source_by_url(session, xml_url)
                existing = await session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user.id,
                        Subscription.source_id == source.id,
                    )
                )
                if existing.scalar_one_or_none() is None:
                    session.add(
                        Subscription(
                            user_id=user.id,
                            source_id=source.id,
                            folder_id=folder_id,
                            custom_name=outline.get("title") or outline.get("text"),
                        )
                    )
                    source.active = True
                    imported += 1
            else:
                folder_name = outline.get("title") or outline.get("text") or "Imported"
                folder = Folder(user_id=user.id, name=folder_name, parent_id=folder_id)
                session.add(folder)
                await session.flush()
                await process(outline, folder.id)

    body_element = root.find("body")
    if body_element is not None:
        await process(body_element, None)
    await session.commit()
    return {"imported": imported}


@router.get("/feeds/export-opml")
async def export_opml(
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> Response:
    result = await session.execute(
        select(Subscription, Source)
        .join(Source, Source.id == Subscription.source_id)
        .where(Subscription.user_id == user.id)
    )
    rows = result.all()

    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "ARESES Export"
    body = ET.SubElement(opml, "body")
    for sub, source in rows:
        ET.SubElement(
            body,
            "outline",
            text=sub.custom_name or source.url,
            title=sub.custom_name or source.url,
            type="rss",
            xmlUrl=source.url,
            htmlUrl=source.site_url or "",
        )

    xml_bytes = ET.tostring(opml, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_bytes, media_type="application/xml")


@router.post("/feeds/bulk-move")
async def bulk_move_feeds(
    body: BulkMove,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if body.folder_id is not None:
        folder_check = await session.execute(
            select(Folder.id).where(
                Folder.id == body.folder_id, Folder.user_id == user.id
            )
        )
        if folder_check.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "folder_not_found", "message": "folder not found"},
            )

    result = await session.execute(
        select(Subscription).where(
            Subscription.id.in_(body.subscription_ids),
            Subscription.user_id == user.id,
        )
    )
    subscriptions = list(result.scalars().all())
    for sub in subscriptions:
        sub.folder_id = body.folder_id
    await session.commit()
    return {"moved": len(subscriptions)}


@router.post("/feeds/bulk-delete")
async def bulk_delete_feeds(
    body: BulkDelete,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Subscription).where(
            Subscription.id.in_(body.subscription_ids),
            Subscription.user_id == user.id,
        )
    )
    subscriptions = list(result.scalars().all())
    deleted = 0
    affected_source_ids: set[int] = set()
    for subscription in subscriptions:
        source_id = subscription.source_id
        await session.execute(
            delete(UserArticleState).where(
                UserArticleState.user_id == user.id,
                UserArticleState.article_id.in_(
                    select(Article.id).where(Article.source_id == source_id)
                ),
            )
        )
        await session.delete(subscription)
        deleted += 1
        affected_source_ids.add(source_id)

    for source_id in affected_source_ids:
        remaining = await session.execute(
            select(Subscription.id).where(Subscription.source_id == source_id)
        )
        if remaining.first() is None:
            source_result = await session.execute(
                select(Source).where(Source.id == source_id)
            )
            source = source_result.scalar_one()
            source.active = False

    await session.commit()
    return {"deleted": deleted}


@router.post("/feeds/preview", response_model=FeedPreviewOut)
async def preview_feed(
    body: FeedPreviewRequest,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    auth = (body.http_username, body.http_password or "") if body.http_username else None
    resolved_url, parsed = await feed_discovery.discover_and_fetch(body.url, auth)

    existing = await session.execute(select(Source.id).where(Source.url == resolved_url))
    already_in_catalog = existing.scalar_one_or_none() is not None

    entries = [
        FeedPreviewEntry(
            title=entry.get("title", "(untitled)"),
            link=entry.get("link"),
            published=entry.get("published"),
        )
        for entry in parsed.entries[:5]
    ]

    return {
        "feed_title": parsed.feed.get("title"),
        "resolved_url": resolved_url,
        "already_in_catalog": already_in_catalog,
        "entries": entries,
    }
