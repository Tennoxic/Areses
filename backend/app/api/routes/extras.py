from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_auth
from app.core.time import utcnow
from app.db.models import (
    Article,
    Folder,
    SavedSearch,
    Source,
    Subscription,
    User,
    UserArticleState,
)
from app.db.session import get_session
from app.schemas.base import CamelModel
from app.services import push_service, settings_service

router = APIRouter(prefix="/api", tags=["extras"])


class PushSubscribeRequest(CamelModel):
    endpoint: str
    keys: dict[str, str]


class PushUnsubscribeRequest(CamelModel):
    endpoint: str


class VapidPublicKeyOut(CamelModel):
    public_key: str


class BackupEntryOut(CamelModel):
    filename: str
    size_bytes: int
    created_at: str


class BackupsListOut(CamelModel):
    backup_enabled: bool
    backup_retention_count: int
    backups: list[BackupEntryOut]


class SubscriptionExportItem(CamelModel):
    url: str
    site_url: str | None
    custom_name: str | None
    folder_id: int | None


class FolderExportItem(CamelModel):
    id: int
    name: str
    parent_id: int | None


class ArticleStateExportItem(CamelModel):
    article_url: str
    article_title: str
    is_read: bool
    starred: bool
    read_later: bool
    read_at: str | None


class SavedSearchExportItem(CamelModel):
    name: str
    query: str


class DataExportOut(CamelModel):
    exported_at: str
    username: str
    folders: list[FolderExportItem]
    subscriptions: list[SubscriptionExportItem]
    article_states: list[ArticleStateExportItem]
    saved_searches: list[SavedSearchExportItem]


@router.get("/push/vapid-public-key", response_model=VapidPublicKeyOut)
async def get_vapid_public_key(
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> VapidPublicKeyOut:
    keys = await push_service.get_or_create_vapid_keys(session)
    return VapidPublicKeyOut(public_key=keys["public_key"])


@router.post("/push/subscribe")
async def push_subscribe(
    body: PushSubscribeRequest,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await push_service.subscribe(
        session,
        user.id,
        endpoint=body.endpoint,
        p256dh=body.keys.get("p256dh", ""),
        auth=body.keys.get("auth", ""),
    )
    return {"status": "ok"}


@router.post("/push/unsubscribe")
async def push_unsubscribe(
    body: PushUnsubscribeRequest,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await push_service.unsubscribe(session, user.id, body.endpoint)
    return {"status": "ok"}


@router.get("/export/my-data", response_model=DataExportOut)
async def export_my_data(
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DataExportOut:
    subs_result = await session.execute(
        select(Subscription, Source)
        .join(Source, Source.id == Subscription.source_id)
        .where(Subscription.user_id == user.id)
    )
    subscriptions = [
        {
            "url": source.url,
            "site_url": source.site_url,
            "custom_name": sub.custom_name,
            "folder_id": sub.folder_id,
        }
        for sub, source in subs_result.all()
    ]

    folders_result = await session.execute(
        select(Folder).where(Folder.user_id == user.id)
    )
    folders = [
        {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id}
        for folder in folders_result.scalars().all()
    ]

    states_result = await session.execute(
        select(UserArticleState, Article)
        .join(Article, Article.id == UserArticleState.article_id)
        .where(UserArticleState.user_id == user.id)
    )
    article_states = [
        {
            "article_url": article.url,
            "article_title": article.title,
            "is_read": state.is_read,
            "starred": state.starred,
            "read_later": state.read_later,
            "read_at": state.read_at.isoformat() if state.read_at else None,
        }
        for state, article in states_result.all()
    ]

    saved_searches_result = await session.execute(
        select(SavedSearch).where(SavedSearch.user_id == user.id)
    )
    saved_searches = [
        {"name": s.name, "query": s.query} for s in saved_searches_result.scalars().all()
    ]

    return DataExportOut(
        exported_at=utcnow().isoformat(),
        username=user.username,
        folders=[FolderExportItem(**f) for f in folders],
        subscriptions=[SubscriptionExportItem(**s) for s in subscriptions],
        article_states=[ArticleStateExportItem(**a) for a in article_states],
        saved_searches=[SavedSearchExportItem(**s) for s in saved_searches],
    )


class BackupSettingsUpdate(CamelModel):
    backup_enabled: bool | None = None
    backup_retention_count: int | None = None


@router.get("/admin/backups", response_model=BackupsListOut)
async def list_backups_route(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> BackupsListOut:
    from app.services import backup_service

    enabled = await settings_service.get_global_setting(session, "backupEnabled")
    retention = await settings_service.get_global_setting(
        session, "backupRetentionCount", "7"
    )
    return BackupsListOut(
        backup_enabled=enabled == "true",
        backup_retention_count=int(retention),
        backups=[BackupEntryOut(**entry) for entry in backup_service.list_backups()],
    )


@router.post("/admin/backups/run-now")
async def run_backup_now_route(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.services import backup_service

    path = await backup_service.run_backup_now(session)
    return {"status": "ok" if path else "no_local_sqlite_db", "path": str(path) if path else None}


@router.delete("/admin/backups/{filename}")
async def delete_backup_route(
    filename: str,
    user: User = Depends(require_admin),
) -> dict:
    from app.services import backup_service

    deleted = backup_service.delete_backup(filename)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "backup_not_found", "message": "backup not found"},
        )
    return {"status": "ok"}


@router.patch("/admin/backups/settings")
async def update_backup_settings_route(
    body: BackupSettingsUpdate,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if body.backup_enabled is not None:
        await settings_service.set_global_setting(
            session, "backupEnabled", "true" if body.backup_enabled else "false"
        )
    if body.backup_retention_count is not None:
        await settings_service.set_global_setting(
            session, "backupRetentionCount", str(body.backup_retention_count)
        )
    return {"status": "ok"}
