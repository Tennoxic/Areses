from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.db.models import Setting

_SENSITIVE_KEYS = {
    "smtpPassword",
    "aiApiKey",
    "vapidPrivateKey",
}


def is_sensitive_key(key: str) -> bool:
    return key in _SENSITIVE_KEYS


async def get_global_setting(
    session: AsyncSession, key: str, default: str | None = None
) -> str | None:
    result = await session.execute(
        select(Setting.value)
        .where(Setting.user_id.is_(None), Setting.key == key)
        .order_by(text("rowid DESC"))
        .limit(1)
    )
    value = result.scalar_one_or_none()
    if value is None:
        return default
    if key in _SENSITIVE_KEYS:
        return decrypt_secret(value)
    return value


async def set_global_setting(session: AsyncSession, key: str, value: str) -> None:
    stored_value = encrypt_secret(value) if key in _SENSITIVE_KEYS else value
    await session.execute(
        delete(Setting).where(Setting.user_id.is_(None), Setting.key == key)
    )
    session.add(Setting(user_id=None, key=key, value=stored_value))
    await session.commit()
