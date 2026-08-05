from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db.models import Folder, Subscription, User
from app.db.session import get_session
from app.schemas.feeds import FolderCreate, FolderOut

router = APIRouter(prefix="/api", tags=["folders"])


@router.post("/folders", response_model=FolderOut)
async def create_folder(
    body: FolderCreate,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> Folder:
    folder = Folder(user_id=user.id, name=body.name, parent_id=body.parent_id)
    session.add(folder)
    await session.commit()
    await session.refresh(folder)
    return folder


@router.get("/folders", response_model=list[FolderOut])
async def list_folders(
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[Folder]:
    result = await session.execute(select(Folder).where(Folder.user_id == user.id))
    return list(result.scalars().all())


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    subs_result = await session.execute(
        select(Subscription).where(Subscription.folder_id == folder_id)
    )
    for sub in subs_result.scalars().all():
        sub.folder_id = None

    child_folders_result = await session.execute(
        select(Folder).where(Folder.parent_id == folder_id)
    )
    for child in child_folders_result.scalars().all():
        child.parent_id = None

    await session.delete(folder)
    await session.commit()
    return {"status": "ok"}
