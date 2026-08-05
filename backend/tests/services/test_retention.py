import datetime

import pytest
from sqlalchemy import select

from app.core.time import utcnow
from app.db.models import Article, Subscription
from app.services import read_state
from tests.services.test_search_parser import _make_subscribed_article, _make_user


@pytest.mark.asyncio
async def test_retention_deletes_old_read_unstarred_single_subscriber_article(db_session):
    user = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user, title="old", content="c", url="https://ret1.example.test"
    )
    await read_state.mark_read(db_session, user.id, article.id)

    from app.db.models import UserArticleState

    result = await db_session.execute(
        select(UserArticleState).where(UserArticleState.article_id == article.id)
    )
    state = result.scalar_one()
    state.read_at = utcnow() - datetime.timedelta(days=31)
    await db_session.commit()

    deleted_count = await read_state.run_retention_cleanup(db_session)
    assert deleted_count == 1

    remaining = await db_session.execute(select(Article).where(Article.id == article.id))
    assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_retention_preserves_starred_article(db_session):
    user = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user, title="starred", content="c", url="https://ret2.example.test"
    )
    await read_state.mark_read(db_session, user.id, article.id)
    await read_state.toggle_star(db_session, user.id, article.id)

    from app.db.models import UserArticleState

    result = await db_session.execute(
        select(UserArticleState).where(UserArticleState.article_id == article.id)
    )
    state = result.scalar_one()
    state.read_at = utcnow() - datetime.timedelta(days=31)
    await db_session.commit()

    await read_state.run_retention_cleanup(db_session)

    remaining = await db_session.execute(select(Article).where(Article.id == article.id))
    assert remaining.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_retention_skips_multi_subscriber_source(db_session):
    user_a = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user_a, title="shared", content="c", url="https://ret3.example.test"
    )

    user_b = await _make_user(db_session)
    db_session.add(Subscription(user_id=user_b.id, source_id=article.source_id))
    await db_session.commit()

    await read_state.mark_read(db_session, user_a.id, article.id)

    from app.db.models import UserArticleState

    result = await db_session.execute(
        select(UserArticleState).where(
            UserArticleState.article_id == article.id, UserArticleState.user_id == user_a.id
        )
    )
    state = result.scalar_one()
    state.read_at = utcnow() - datetime.timedelta(days=31)
    await db_session.commit()

    await read_state.run_retention_cleanup(db_session)

    remaining = await db_session.execute(select(Article).where(Article.id == article.id))
    assert remaining.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_retention_keeps_recently_read_article(db_session):
    user = await _make_user(db_session)
    article = await _make_subscribed_article(
        db_session, user, title="recent", content="c", url="https://ret4.example.test"
    )
    await read_state.mark_read(db_session, user.id, article.id)

    await read_state.run_retention_cleanup(db_session)

    remaining = await db_session.execute(select(Article).where(Article.id == article.id))
    assert remaining.scalar_one_or_none() is not None
