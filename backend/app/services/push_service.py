from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PushSubscription
from app.services import settings_service


async def get_or_create_vapid_keys(session: AsyncSession) -> dict:
    public_key = await settings_service.get_global_setting(session, "vapidPublicKey")
    private_key = await settings_service.get_global_setting(session, "vapidPrivateKey")
    if public_key and private_key:
        return {"public_key": public_key, "private_key": private_key}

    import base64

    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid02

    vapid = Vapid02()
    vapid.generate_keys()
    private_pem = vapid.private_pem().decode("utf-8")
    public_raw = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public_raw).decode("utf-8").rstrip("=")

    await settings_service.set_global_setting(session, "vapidPrivateKey", private_pem)
    await settings_service.set_global_setting(session, "vapidPublicKey", public_b64)
    return {"public_key": public_b64, "private_key": private_pem}


async def subscribe(
    session: AsyncSession, user_id: int, endpoint: str, p256dh: str, auth: str
) -> None:
    result = await session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.user_id = user_id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        session.add(
            PushSubscription(
                user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth
            )
        )
    await session.commit()


async def unsubscribe(session: AsyncSession, user_id: int, endpoint: str) -> None:
    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        await session.delete(existing)
        await session.commit()


async def notify_user(
    session: AsyncSession, user_id: int, title: str, body: str, url: str = "/"
) -> None:
    try:
        from pywebpush import WebPushException, webpush
    except Exception:
        return

    keys = await get_or_create_vapid_keys(session)
    result = await session.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subscriptions = list(result.scalars().all())
    if not subscriptions:
        return

    import asyncio
    import json

    payload = json.dumps({"title": title, "body": body, "url": url})
    dead_endpoints = []
    for sub in subscriptions:
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=keys["private_key"],
                vapid_claims={"sub": "mailto:admin@areses.local"},
            )
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                dead_endpoints.append(sub.endpoint)
        except Exception:
            continue

    for endpoint in dead_endpoints:
        await unsubscribe(session, user_id, endpoint)
