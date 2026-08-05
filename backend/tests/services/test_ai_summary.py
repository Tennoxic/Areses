import pytest

from app.core.time import utcnow
from app.db.models import Article, Source, Subscription
from app.services import ai_summary
from tests.services.test_search_parser import _make_user


async def _make_source_with_subscription(db_session, user, *, summarize_enabled: bool, url: str) -> Source:
    source = Source(url=url, next_fetch_at=utcnow())
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    db_session.add(
        Subscription(user_id=user.id, source_id=source.id, summarize_enabled=summarize_enabled)
    )
    await db_session.commit()
    return source


@pytest.mark.asyncio
async def test_article_not_enqueued_without_summarize_subscriber(db_session):
    user = await _make_user(db_session)
    source = await _make_source_with_subscription(
        db_session, user, summarize_enabled=False, url="https://ai1.example.test"
    )
    article = Article(
        source_id=source.id,
        url="https://ai1.example.test/a",
        title="t",
        content="body text " * 10,
        word_count=20,
        reading_time_minutes=1,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    await ai_summary.maybe_enqueue_summary(db_session, article)
    await db_session.refresh(article)
    assert article.summary_pending is False


@pytest.mark.asyncio
async def test_article_enqueued_with_summarize_subscriber(db_session):
    user = await _make_user(db_session)
    source = await _make_source_with_subscription(
        db_session, user, summarize_enabled=True, url="https://ai2.example.test"
    )
    article = Article(
        source_id=source.id,
        url="https://ai2.example.test/a",
        title="t",
        content="body text " * 10,
        word_count=20,
        reading_time_minutes=1,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    await ai_summary.maybe_enqueue_summary(db_session, article)
    await db_session.refresh(article)
    assert article.summary_pending is True


@pytest.mark.asyncio
async def test_process_pending_summaries_writes_summary_on_success(db_session, monkeypatch):
    user = await _make_user(db_session)
    source = await _make_source_with_subscription(
        db_session, user, summarize_enabled=True, url="https://ai3.example.test"
    )
    article = Article(
        source_id=source.id,
        url="https://ai3.example.test/a",
        title="t",
        content="body text " * 10,
        word_count=20,
        reading_time_minutes=1,
        summary_pending=True,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    async def _fake_get_model_response(provider, model, prompt, api_key, base_url):
        return "a short mocked summary"

    monkeypatch.setattr(ai_summary, "get_model_response", _fake_get_model_response)

    processed = await ai_summary.process_pending_summaries(db_session)
    assert processed >= 1

    await db_session.refresh(article)
    assert article.summary_pending is False
    assert article.ai_summary == "a short mocked summary"


@pytest.mark.asyncio
async def test_process_pending_summaries_clears_flag_on_provider_failure(db_session, monkeypatch):
    user = await _make_user(db_session)
    source = await _make_source_with_subscription(
        db_session, user, summarize_enabled=True, url="https://ai4.example.test"
    )
    article = Article(
        source_id=source.id,
        url="https://ai4.example.test/a",
        title="t",
        content="body text " * 10,
        word_count=20,
        reading_time_minutes=1,
        summary_pending=True,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    async def _failing_get_model_response(provider, model, prompt, api_key, base_url):
        raise RuntimeError("provider unreachable")

    monkeypatch.setattr(ai_summary, "get_model_response", _failing_get_model_response)

    await ai_summary.process_pending_summaries(db_session)

    await db_session.refresh(article)
    assert article.summary_pending is False
    assert article.ai_summary is None
