from fastapi import APIRouter, Depends, HTTPException, status
from httpx import HTTPStatusError, RequestError
from pydantic import ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.models import (
    Folder,
    PasswordResetToken,
    SavedSearch,
    Source,
    Subscription,
    User,
    UserArticleState,
    UserSession,
)
from app.db.session import get_session
from app.schemas.base import CamelModel
from app.services import settings_service
from app.services.providers.client import ProviderError, get_model_response

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserOut(CamelModel):
    id: int
    username: str
    email: str
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(CamelModel):
    key: str
    value: str


@router.get("/users", response_model=list[UserOut])
async def list_users(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    result = await session.execute(select(User))
    return list(result.scalars().all())


class RoleUpdate(CamelModel):
    is_admin: bool


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if target.is_admin and not body.is_admin:
        admin_count_result = await session.execute(
            select(User).where(User.is_admin.is_(True))
        )
        if len(admin_count_result.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "last_admin_demote", "message": "cannot demote the last admin"},
            )

    target.is_admin = body.is_admin
    await session.commit()
    await session.refresh(target)
    return target


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if target.is_admin:
        admin_count_result = await session.execute(
            select(User).where(User.is_admin.is_(True))
        )
        if len(admin_count_result.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "last_admin_delete", "message": "cannot delete the last admin"},
            )

    orphaned_sources_result = await session.execute(
        select(Subscription.source_id).where(Subscription.user_id == user_id)
    )
    affected_source_ids = {row[0] for row in orphaned_sources_result.all()}

    await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
    await session.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    )
    await session.execute(
        delete(UserArticleState).where(UserArticleState.user_id == user_id)
    )
    await session.execute(delete(Subscription).where(Subscription.user_id == user_id))
    await session.execute(delete(Folder).where(Folder.user_id == user_id))
    await session.execute(delete(SavedSearch).where(SavedSearch.user_id == user_id))
    await session.delete(target)

    for source_id in affected_source_ids:
        remaining = await session.execute(
            select(Subscription.id).where(Subscription.source_id == source_id)
        )
        if remaining.first() is None:
            source_result = await session.execute(
                select(Source).where(Source.id == source_id)
            )
            source = source_result.scalar_one_or_none()
            if source is not None:
                source.active = False

    await session.commit()
    return {"status": "ok"}


@router.post("/settings")
async def update_setting(
    body: SettingUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await settings_service.set_global_setting(session, body.key, body.value)
    return {"status": "ok"}


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if settings_service.is_sensitive_key(key):
        value = await settings_service.get_global_setting(session, key)
        return {"key": key, "value": None, "isSet": bool(value)}
    value = await settings_service.get_global_setting(session, key)
    return {"key": key, "value": value}


class AITestRequest(CamelModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


class AITestResponse(CamelModel):
    success: bool
    message: str


@router.post("/ai/test", response_model=AITestResponse)
async def test_ai_provider(
    body: AITestRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AITestResponse:
    api_key = body.api_key or await settings_service.get_global_setting(session, "aiApiKey")
    base_url = body.base_url or await settings_service.get_global_setting(session, "aiBaseUrl")
    try:
        await get_model_response(
            body.provider, body.model, "Reply with exactly one word: OK", api_key, base_url
        )
    except ProviderError as error:
        return AITestResponse(success=False, message=str(error))
    except HTTPStatusError as error:
        return AITestResponse(
            success=False,
            message=f"provider responded with HTTP {error.response.status_code}",
        )
    except RequestError:
        return AITestResponse(success=False, message="could not reach the provider (network error)")
    return AITestResponse(success=True, message="connection successful")
