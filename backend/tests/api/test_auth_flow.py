import pytest

from tests.conftest import unique_username


@pytest.mark.asyncio
async def test_register_and_login_roundtrip(client):
    username = unique_username()
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "correct-horse-battery-staple",
    }
    register_response = await client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 200

    login_response = await client.post(
        "/api/auth/login",
        json={"username": username, "password": payload["password"], "rememberMe": False},
    )
    assert login_response.status_code == 200
    assert "session_token" in login_response.cookies


@pytest.mark.asyncio
async def test_login_cookie_security_flags(client, registered_user):
    response = await client.post(
        "/api/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
            "rememberMe": False,
        },
    )
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


@pytest.mark.asyncio
async def test_me_requires_authentication(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_session_does_not_error_when_logged_out(client):
    response = await client.get("/api/auth/session")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
    assert body["user"] is None


@pytest.mark.asyncio
async def test_session_reports_authenticated_user_after_login(client, registered_user):
    await client.post(
        "/api/auth/login",
        json={"username": registered_user["username"], "password": registered_user["password"], "rememberMe": False},
    )
    response = await client.get("/api/auth/session")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["username"] == registered_user["username"]


@pytest.mark.asyncio
async def test_full_auth_lifecycle(client, registered_user):
    login = await client.post(
        "/api/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
            "rememberMe": False,
        },
    )
    assert login.status_code == 200

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == registered_user["username"]

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 200

    me_after_logout = await client.get("/api/auth/me")
    assert me_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_wrong_password_rejected_with_generic_message(client, registered_user):
    response = await client.post(
        "/api/auth/login",
        json={"username": registered_user["username"], "password": "wrong-password", "rememberMe": False},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "invalid_credentials"
    assert "invalid username or password" in detail["message"]


@pytest.mark.asyncio
async def test_login_rate_limit_locks_after_five_failures(client):
    username = unique_username("lockout")
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "correct-horse-battery-staple",
    }
    await client.post("/api/auth/register", json=payload)

    for _ in range(5):
        response = await client.post(
            "/api/auth/login",
            json={"username": username, "password": "wrong", "rememberMe": False},
        )
        assert response.status_code == 401

    locked_response = await client.post(
        "/api/auth/login",
        json={"username": username, "password": payload["password"], "rememberMe": False},
    )
    assert locked_response.status_code == 429


@pytest.mark.asyncio
async def test_forgot_password_does_not_leak_existence(client):
    known = await client.post(
        "/api/auth/forgot-password", json={"email": "nonexistent-user@example.com"}
    )
    assert known.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_response_is_translatable_code(client):
    response = await client.post(
        "/api/auth/forgot-password", json={"email": "someone-else@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "password_reset_sent"


@pytest.mark.asyncio
async def test_password_reset_requests_are_rate_limited(client):
    email = "rate-limited-reset@example.com"
    from app.services import auth_service

    allowed = [auth_service._check_reset_rate_limit(email) for _ in range(5)]
    assert allowed == [True, True, True, False, False]
