from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.core.config import settings
from app.db.models import User
from app.db.session import get_session
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
async def register_route(
    body: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> User:
    return await auth_service.register(session, body.username, body.email, body.password)


@router.post("/login")
async def login_route(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict:
    token = await auth_service.login(
        session, body.username, body.password, body.remember_me
    )
    max_age = 60 * 60 * 24 * (90 if body.remember_me else 7)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=not settings.local_mode,
        samesite="lax",
        max_age=max_age,
    )
    return {"status": "ok"}


@router.post("/logout")
async def logout_route(
    response: Response,
    session_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if session_token:
        await auth_service.logout(session, session_token)
    response.delete_cookie("session_token")
    return {"status": "ok"}


@router.post("/forgot-password")
async def forgot_password_route(
    body: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    await auth_service.request_password_reset(session, body.email)
    return {"status": "password_reset_sent"}


@router.post("/reset-password")
async def reset_password_route(
    body: ResetPasswordRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    await auth_service.reset_password(session, body.token, body.new_password)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me_route(user: User = Depends(require_auth)) -> User:
    return user
