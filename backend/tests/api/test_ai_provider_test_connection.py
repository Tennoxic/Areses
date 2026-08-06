import pytest
from sqlalchemy import update

from app.db.models import User
from tests.conftest import unique_username


async def _make_admin_and_login(client, db_session, username_prefix="aitest"):
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


@pytest.mark.asyncio
async def test_ai_test_requires_admin(client, registered_user):
    await client.post(
        "/api/auth/login",
        json={"username": registered_user["username"], "password": registered_user["password"], "rememberMe": False},
    )
    response = await client.post(
        "/api/admin/ai/test",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "apiKey": "x"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ai_test_reports_success(client, db_session, monkeypatch):
    await _make_admin_and_login(client, db_session)

    async def _fake_ok(provider, model, prompt, api_key, base_url):
        return "OK"

    monkeypatch.setattr("app.api.routes.admin.get_model_response", _fake_ok)

    response = await client.post(
        "/api/admin/ai/test",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "apiKey": "sk-test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_ai_test_reports_provider_error_without_raising(client, db_session, monkeypatch):
    await _make_admin_and_login(client, db_session)

    from app.services.providers.client import ProviderError

    async def _fake_fail(provider, model, prompt, api_key, base_url):
        raise ProviderError("missing api key for anthropic")

    monkeypatch.setattr("app.api.routes.admin.get_model_response", _fake_fail)

    response = await client.post(
        "/api/admin/ai/test",
        json={"provider": "anthropic", "model": "claude-sonnet-5"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "missing api key" in body["message"]
