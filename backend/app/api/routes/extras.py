from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
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
from app.services import feed_discovery, push_service, settings_service

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


class DataImportRequest(CamelModel):
    folders: list[FolderExportItem] = []
    subscriptions: list[SubscriptionExportItem] = []
    article_states: list[ArticleStateExportItem] = []
    saved_searches: list[SavedSearchExportItem] = []
    mode: Literal["merge", "overwrite"] = "merge"


class DataImportOut(CamelModel):
    folders_created: int
    subscriptions_created: int
    subscriptions_skipped: int
    article_states_applied: int
    article_states_skipped: int
    saved_searches_created: int


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


@router.post("/import/my-data", response_model=DataImportOut)
async def import_my_data(
    body: DataImportRequest,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DataImportOut:
    if body.mode == "overwrite":
        await session.execute(delete(UserArticleState).where(UserArticleState.user_id == user.id))
        await session.execute(delete(Subscription).where(Subscription.user_id == user.id))
        await session.execute(delete(SavedSearch).where(SavedSearch.user_id == user.id))
        await session.execute(delete(Folder).where(Folder.user_id == user.id))
        await session.flush()

    existing_folders_result = await session.execute(
        select(Folder).where(Folder.user_id == user.id)
    )
    folder_id_by_name = {f.name: f.id for f in existing_folders_result.scalars().all()}

    folder_id_remap: dict[int, int] = {}
    folders_created = 0
    for item in body.folders:
        if item.name in folder_id_by_name:
            folder_id_remap[item.id] = folder_id_by_name[item.name]
            continue
        folder = Folder(user_id=user.id, name=item.name, parent_id=None)
        session.add(folder)
        await session.flush()
        folder_id_remap[item.id] = folder.id
        folder_id_by_name[item.name] = folder.id
        folders_created += 1

    for item in body.folders:
        if item.parent_id is None:
            continue
        new_id = folder_id_remap.get(item.id)
        new_parent_id = folder_id_remap.get(item.parent_id)
        if new_id is not None and new_parent_id is not None and new_id != new_parent_id:
            await session.execute(
                update(Folder).where(Folder.id == new_id).values(parent_id=new_parent_id)
            )

    existing_subs_result = await session.execute(
        select(Subscription.source_id).where(Subscription.user_id == user.id)
    )
    subscribed_source_ids = {row[0] for row in existing_subs_result.all()}

    subscriptions_created = 0
    subscriptions_skipped = 0
    for item in body.subscriptions:
        source = await feed_discovery.get_or_create_source_by_url(session, item.url)
        if source.id in subscribed_source_ids:
            subscriptions_skipped += 1
            continue
        mapped_folder_id = (
            folder_id_remap.get(item.folder_id) if item.folder_id is not None else None
        )
        session.add(
            Subscription(
                user_id=user.id,
                source_id=source.id,
                folder_id=mapped_folder_id,
                custom_name=item.custom_name,
            )
        )
        source.active = True
        subscribed_source_ids.add(source.id)
        subscriptions_created += 1

    article_states_applied = 0
    article_states_skipped = 0
    for item in body.article_states:
        article_result = await session.execute(
            select(Article.id).where(Article.url == item.article_url)
        )
        article_id = article_result.scalar_one_or_none()
        if article_id is None:
            article_states_skipped += 1
            continue
        existing_state_result = await session.execute(
            select(UserArticleState).where(
                UserArticleState.user_id == user.id,
                UserArticleState.article_id == article_id,
            )
        )
        state = existing_state_result.scalar_one_or_none()
        if state is None:
            state = UserArticleState(user_id=user.id, article_id=article_id)
            session.add(state)
        state.is_read = state.is_read or item.is_read
        state.starred = state.starred or item.starred
        state.read_later = state.read_later or item.read_later
        article_states_applied += 1

    existing_searches_result = await session.execute(
        select(SavedSearch.name).where(SavedSearch.user_id == user.id)
    )
    existing_search_names = {row[0] for row in existing_searches_result.all()}

    saved_searches_created = 0
    for item in body.saved_searches:
        if item.name in existing_search_names:
            continue
        session.add(SavedSearch(user_id=user.id, name=item.name, query=item.query))
        existing_search_names.add(item.name)
        saved_searches_created += 1

    await session.commit()
    return DataImportOut(
        folders_created=folders_created,
        subscriptions_created=subscriptions_created,
        subscriptions_skipped=subscriptions_skipped,
        article_states_applied=article_states_applied,
        article_states_skipped=article_states_skipped,
        saved_searches_created=saved_searches_created,
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
