import pytest

from app.services import read_state
from tests.services.test_search_parser import _make_subscribed_article, _make_user


@pytest.mark.asyncio
async def test_mark_read_and_unread_roundtrip(db_session):
    user = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user, title="t", content="c", url="https://rs1.example.test"
    )

    await read_state.mark_read(db_session, user.id, article.id)
    counts = await read_state.get_unread_counts(db_session, user.id)
    assert counts.get(article.source_id, 0) == 0

    await read_state.mark_unread(db_session, user.id, article.id)
    counts = await read_state.get_unread_counts(db_session, user.id)
    assert counts.get(article.source_id, 0) == 1


@pytest.mark.asyncio
async def test_toggle_star_flips_state(db_session):
    user = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user, title="t", content="c", url="https://rs2.example.test"
    )

    first = await read_state.toggle_star(db_session, user.id, article.id)
    second = await read_state.toggle_star(db_session, user.id, article.id)
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_mark_all_read_scoped_to_source(db_session):
    user = await _make_user(db_session)
    a1 = await _make_subscribed_article(db_session, user, title="a1", content="c", url="https://rs3.example.test")
    a2 = await _make_subscribed_article(db_session, user, title="a2", content="c", url="https://rs4.example.test")

    await read_state.mark_all_read(db_session, user.id, source_id=a1.source_id)

    counts = await read_state.get_unread_counts(db_session, user.id)
    assert counts.get(a1.source_id, 0) == 0
    assert counts.get(a2.source_id, 0) == 1


@pytest.mark.asyncio
async def test_scroll_position_persists(db_session):
    user = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user, title="t", content="c", url="https://rs5.example.test"
    )
    await read_state.update_scroll_position(db_session, user.id, article.id, 0.42)

    from sqlalchemy import select

    from app.db.models import UserArticleState

    result = await db_session.execute(
        select(UserArticleState).where(
            UserArticleState.user_id == user.id, UserArticleState.article_id == article.id
        )
    )
    state = result.scalar_one()
    assert state.scroll_position == pytest.approx(0.42)
