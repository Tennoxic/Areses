from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db.models import SavedSearch, User
from app.db.session import get_session
from app.schemas.base import CamelModel

router = APIRouter(prefix="/api/saved-searches", tags=["saved-searches"])


class SavedSearchCreate(CamelModel):
    name: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=500)


class SavedSearchOut(CamelModel):
    id: int
    name: str
    query: str

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=SavedSearchOut)
async def create_saved_search(
    body: SavedSearchCreate,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> SavedSearch:
    saved = SavedSearch(user_id=user.id, name=body.name, query=body.query)
    session.add(saved)
    await session.commit()
    await session.refresh(saved)
    return saved


@router.get("", response_model=list[SavedSearchOut])
async def list_saved_searches(
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[SavedSearch]:
    result = await session.execute(
        select(SavedSearch).where(SavedSearch.user_id == user.id)
    )
    return list(result.scalars().all())


@router.delete("/{saved_search_id}")
async def delete_saved_search(
    saved_search_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(SavedSearch).where(
            SavedSearch.id == saved_search_id, SavedSearch.user_id == user.id
        )
    )
    saved = result.scalar_one_or_none()
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(saved)
    await session.commit()
    return {"status": "ok"}
