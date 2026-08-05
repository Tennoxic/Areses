import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_tmp_dir = tempfile.mkdtemp(prefix="areses-test-")
_DB_PATH = os.path.join(_tmp_dir, "test.db")

os.environ["ARESES_DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
os.environ["ARESES_LOCAL_MODE"] = "true"
os.environ["ARESES_BASE_URL"] = "http://testserver"

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=str(_BACKEND_DIR),
    env=os.environ.copy(),
    check=True,
)

import pytest_asyncio              
from httpx import ASGITransport, AsyncClient              

from app.db.session import async_session_maker              
from app.main import app              


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


def unique_username(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@pytest_asyncio.fixture
async def registered_user(client):
    username = unique_username()
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "correct-horse-battery-staple",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    return payload
