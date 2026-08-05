import pytest
from sqlalchemy import select, update

from app.db.models import User
from tests.conftest import unique_username


async def _make_admin_and_login(client, db_session, username_prefix="admin"):
    username = unique_username(username_prefix)
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "correct-horse-battery-staple",
    }
    await client.post("/api/auth/register", json=payload)
    await db_session.execute(
        update(User).where(User.username == username).values(is_admin=True)
    )
    await db_session.commit()
    await client.post(
        "/api/auth/login",
        json={"username": username, "password": payload["password"], "rememberMe": False},
    )
    result = await db_session.execute(select(User).where(User.username == username))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_routes(client, registered_user, db_session):
    await db_session.execute(
        update(User).where(User.username == registered_user["username"]).values(is_admin=False)
    )
    await db_session.commit()

    await client.post(
        "/api/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
            "rememberMe": False,
        },
    )
    response = await client.get("/api/admin/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_users(client, db_session):
    await _make_admin_and_login(client, db_session)
    response = await client.get("/api/admin/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_admin_can_demote_another_admin(client, db_session):
    await _make_admin_and_login(client, db_session)

    other_username = unique_username("second_admin")
    other_payload = {
        "username": other_username,
        "email": f"{other_username}@example.com",
        "password": "correct-horse-battery-staple",
    }
    await client.post("/api/auth/register", json=other_payload)
    await db_session.execute(
        update(User).where(User.username == other_username).values(is_admin=True)
    )
    await db_session.commit()
    result = await db_session.execute(select(User).where(User.username == other_username))
    other = result.scalar_one()

    response = await client.patch(
        f"/api/admin/users/{other.id}/role", json={"isAdmin": False}
    )
    assert response.status_code == 200
    assert response.json()["isAdmin"] is False


@pytest.mark.asyncio
async def test_cannot_demote_the_last_admin(client, db_session):
    admin = await _make_admin_and_login(client, db_session)

    await db_session.execute(update(User).values(is_admin=False))
    await db_session.execute(
        update(User).where(User.id == admin.id).values(is_admin=True)
    )
    await db_session.commit()

    response = await client.patch(
        f"/api/admin/users/{admin.id}/role", json={"isAdmin": False}
    )
    assert response.status_code == 400
    assert "last admin" in response.json()["detail"]["message"]
