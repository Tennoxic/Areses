from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.services import auth_service


async def require_auth(
    request: Request,
    session: AsyncSession = Depends(get_session),
    session_token: str | None = Cookie(default=None),
) -> User:
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "not authenticated"},
        )
    user = await auth_service.get_user_from_token(session, session_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "not authenticated"},
        )
    request.state.user_id = user.id
    return user


async def require_admin(user: User = Depends(require_auth)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "admin_required", "message": "admin privileges required"},
        )
    return user
