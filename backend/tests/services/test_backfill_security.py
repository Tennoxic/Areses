import pytest
from sqlalchemy import select

from app.cli import cmd_backfill_security
from app.core.crypto import decrypt_secret
from app.core.time import utcnow
from app.db.models import Article, Setting, Source


class _Args:
    pass


@pytest.mark.asyncio
async def test_backfill_security_sanitizes_titles_and_encrypts_secrets(db_session, monkeypatch):
    import app.cli as cli_module

    monkeypatch.setattr(cli_module, "async_session_maker", lambda: _FakeSessionCtx(db_session))

    source = Source(
        url="https://backfill-test.example.test",
        next_fetch_at=utcnow(),
        http_password="plaintext-http-pw",
    )
    db_session.add(source)
    await db_session.flush()
    article = Article(
        source_id=source.id,
        url="https://backfill-test.example.test/a1",
        title="<script>alert(1)</script>Hello",
        author="<b>Bad</b> Author",
        content="fine",
        published_at=utcnow(),
    )
    db_session.add(article)
    db_session.add(Setting(user_id=None, key="smtpPassword", value="plaintext-smtp-pw"))
    await db_session.commit()

    await cmd_backfill_security(_Args())

    await db_session.refresh(article)
    assert article.title == "Hello"
    assert article.author == "Bad Author"

    await db_session.refresh(source)
    assert source.http_password != "plaintext-http-pw"
    assert decrypt_secret(source.http_password) == "plaintext-http-pw"

    setting = (
        await db_session.execute(select(Setting).where(Setting.key == "smtpPassword"))
    ).scalar_one()
    assert setting.value != "plaintext-smtp-pw"
    assert decrypt_secret(setting.value) == "plaintext-smtp-pw"

    source_password_before = source.http_password
    setting_value_before = setting.value
    await cmd_backfill_security(_Args())
    await db_session.refresh(source)
    refreshed_setting = (
        await db_session.execute(select(Setting).where(Setting.key == "smtpPassword"))
    ).scalar_one()
    assert source.http_password == source_password_before
    assert refreshed_setting.value == setting_value_before


class _FakeSessionCtx:

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info):
        return False
