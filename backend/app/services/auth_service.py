import asyncio
import datetime
import logging
import smtplib
import time
from email.message import EmailMessage

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_token, hash_password, verify_password
from app.core.time import utcnow
from app.db.models import PasswordResetToken, User, UserSession
from app.services import settings_service

_logger = logging.getLogger(__name__)

_failed_attempts: dict[str, list[float]] = {}
_LOCKOUT_THRESHOLD = 5
_LOCKOUT_SECONDS = 60
_MAX_TRACKED_USERNAMES = 10_000

_reset_requests: dict[str, list[float]] = {}
_RESET_LOCKOUT_THRESHOLD = 3
_RESET_LOCKOUT_SECONDS = 15 * 60


def _check_reset_rate_limit(email: str) -> bool:
    now = time.monotonic()
    attempts = [t for t in _reset_requests.get(email, []) if now - t < _RESET_LOCKOUT_SECONDS]
    if len(attempts) >= _RESET_LOCKOUT_THRESHOLD:
        _reset_requests[email] = attempts
        return False
    attempts.append(now)
    if len(_reset_requests) >= _MAX_TRACKED_USERNAMES and email not in _reset_requests:
        _reset_requests.clear()
    _reset_requests[email] = attempts
    return True


def _check_rate_limit(username: str) -> None:
    now = time.monotonic()
    attempts = [t for t in _failed_attempts.get(username, []) if now - t < _LOCKOUT_SECONDS]
    if attempts:
        _failed_attempts[username] = attempts
    else:
        _failed_attempts.pop(username, None)
    if len(attempts) >= _LOCKOUT_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "too many failed login attempts, try again later"},
        )


def _record_failed_attempt(username: str) -> None:
    if username not in _failed_attempts and len(_failed_attempts) >= _MAX_TRACKED_USERNAMES:
        now = time.monotonic()
        expired = [
            tracked
            for tracked, attempts in _failed_attempts.items()
            if all(now - t >= _LOCKOUT_SECONDS for t in attempts)
        ]
        for tracked in expired:
            _failed_attempts.pop(tracked, None)
        if len(_failed_attempts) >= _MAX_TRACKED_USERNAMES:
            _failed_attempts.pop(next(iter(_failed_attempts)), None)
    _failed_attempts.setdefault(username, []).append(time.monotonic())


def _clear_failed_attempts(username: str) -> None:
    _failed_attempts.pop(username, None)


async def register(session: AsyncSession, username: str, email: str, password: str) -> User:
    result = await session.execute(select(User.id))
    users_exist = result.first() is not None

    if users_exist:
        registration_enabled = await settings_service.get_global_setting(
            session, "registrationEnabled", "true"
        )
        if registration_enabled == "false":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "registration_disabled", "message": "registration is disabled"},
            )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_admin=not users_exist,
    )
    session.add(user)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "account_conflict", "message": "username or email already exists"},
        ) from exc
    await session.refresh(user)
    return user


async def login(
    session: AsyncSession, username: str, password: str, remember_me: bool
) -> str:
    _check_rate_limit(username)

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(user.password_hash, password):
        _record_failed_attempt(username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "invalid username or password"},
        )

    _clear_failed_attempts(username)

    token = generate_token()
    ttl_days = 90 if remember_me else 7
    expires_at = utcnow() + datetime.timedelta(days=ttl_days)
    session.add(UserSession(token=token, user_id=user.id, expires_at=expires_at))
    await session.commit()
    return token


async def logout(session: AsyncSession, token: str) -> None:
    await session.execute(delete(UserSession).where(UserSession.token == token))
    await session.commit()


async def get_user_from_token(session: AsyncSession, token: str) -> User | None:
    result = await session.execute(
        select(UserSession).where(UserSession.token == token)
    )
    user_session = result.scalar_one_or_none()
    if user_session is None:
        return None
    if user_session.expires_at < utcnow():
        return None
    result = await session.execute(select(User).where(User.id == user_session.user_id))
    return result.scalar_one_or_none()


def _send_email_sync(smtp_host: str, smtp_port: int, smtp_user, smtp_password, message: EmailMessage) -> None:
    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


async def request_password_reset(session: AsyncSession, email: str) -> None:
    if not _check_reset_rate_limit(email):
        return

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        return

    token = generate_token()
    expires_at = utcnow() + datetime.timedelta(hours=1)
    session.add(
        PasswordResetToken(token=token, user_id=user.id, expires_at=expires_at)
    )
    await session.commit()

    smtp_host = await settings_service.get_global_setting(session, "smtpHost")
    if not smtp_host:
        return

    base_url = await settings_service.get_global_setting(
        session, "baseUrl", settings.base_url
    )
    smtp_port = await settings_service.get_global_setting(session, "smtpPort", "587")
    smtp_user = await settings_service.get_global_setting(session, "smtpUser")
    smtp_password = await settings_service.get_global_setting(session, "smtpPassword")
    smtp_from = await settings_service.get_global_setting(session, "smtpFrom")

    reset_link = f"{base_url}/reset-password?token={token}"
    message = EmailMessage()
    message["Subject"] = "ARESES password reset"
    message["From"] = smtp_from or smtp_user
    message["To"] = email
    message.set_content(f"Reset your password: {reset_link}")

    try:
        await asyncio.to_thread(
            _send_email_sync, smtp_host, int(smtp_port), smtp_user, smtp_password, message
        )
    except Exception:
        _logger.exception("failed to send password-reset email")


async def reset_password(session: AsyncSession, token: str, new_password: str) -> None:
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset_token = result.scalar_one_or_none()

    if reset_token is None or reset_token.expires_at < utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_reset_token", "message": "invalid or expired token"},
        )

    result = await session.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one()
    user.password_hash = hash_password(new_password)

    await session.execute(
        delete(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    await session.execute(
        delete(UserSession).where(UserSession.user_id == user.id)
    )
    await session.commit()
