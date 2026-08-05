import datetime

import pytest
from sqlalchemy import select

from app.core.time import utcnow
from app.db.models import Article, Folder, Source, Subscription, User
from app.services import search_service
from app.services.auth_service import register
from tests.conftest import unique_username


async def _make_user(db_session) -> User:
    username = unique_username("search")
    return await register(db_session, username, f"{username}@example.com", "password123456")


async def _make_subscribed_article(db_session, user: User, *, title: str, content: str, url: str) -> Article:
    source = Source(url=url, next_fetch_at=utcnow())
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    db_session.add(Subscription(user_id=user.id, source_id=source.id))
    await db_session.commit()

    article = Article(
        source_id=source.id,
        url=f"{url}/article",
        title=title,
        content=content,
        word_count=len(content.split()),
        reading_time_minutes=1,
        published_at=utcnow(),
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)
    return article


@pytest.mark.asyncio
async def test_simple_term_matches_via_fts(db_session):
    user = await _make_user(db_session)
    await _make_subscribed_article(
        db_session, user, title="Rust ownership explained", content="borrow checker rules", url="https://s1.example.test"
    )
    await _make_subscribed_article(
        db_session, user, title="Python typing", content="static analysis notes", url="https://s2.example.test"
    )

    expr = search_service.parse_search_query("rust", user.id)
    result = await db_session.execute(select(Article).where(expr))
    titles = {a.title for a in result.scalars().all()}
    assert titles == {"Rust ownership explained"}


@pytest.mark.asyncio
async def test_and_or_not_boolean_combinators(db_session):
    user = await _make_user(db_session)
    await _make_subscribed_article(
        db_session, user, title="alpha beta", content="x", url="https://b1.example.test"
    )
    await _make_subscribed_article(
        db_session, user, title="alpha gamma", content="x", url="https://b2.example.test"
    )
    await _make_subscribed_article(
        db_session, user, title="delta", content="x", url="https://b3.example.test"
    )

    and_expr = search_service.parse_search_query("alpha AND beta", user.id)
    result = await db_session.execute(select(Article).where(and_expr))
    assert {a.title for a in result.scalars().all()} == {"alpha beta"}

    or_expr = search_service.parse_search_query("beta OR delta", user.id)
    result = await db_session.execute(select(Article).where(or_expr))
    assert {a.title for a in result.scalars().all()} == {"alpha beta", "delta"}

    not_expr = search_service.parse_search_query("alpha -beta", user.id)
    result = await db_session.execute(select(Article).where(not_expr))
    assert {a.title for a in result.scalars().all()} == {"alpha gamma"}


@pytest.mark.asyncio
async def test_intitle_field_operator(db_session):
    user = await _make_user(db_session)
    await _make_subscribed_article(
        db_session, user, title="Keyword in title", content="unrelated body text", url="https://f1.example.test"
    )
    await _make_subscribed_article(
        db_session, user, title="No match here", content="keyword only in body", url="https://f2.example.test"
    )

    expr = search_service.parse_search_query("intitle:keyword", user.id)
    result = await db_session.execute(select(Article).where(expr))
    assert {a.title for a in result.scalars().all()} == {"Keyword in title"}


@pytest.mark.asyncio
async def test_regex_operator(db_session):
    user = await _make_user(db_session)
    await _make_subscribed_article(
        db_session, user, title="Version 2026.07", content="release notes", url="https://r1.example.test"
    )
    await _make_subscribed_article(
        db_session, user, title="No version here", content="misc", url="https://r2.example.test"
    )

    expr = search_service.parse_search_query(r"/\d{4}\.\d{2}/", user.id)
    result = await db_session.execute(select(Article).where(expr))
    assert {a.title for a in result.scalars().all()} == {"Version 2026.07"}


@pytest.mark.asyncio
async def test_date_range_operator(db_session):
    user = await _make_user(db_session)
    old_article = await _make_subscribed_article(
        db_session, user, title="Old", content="x", url="https://d1.example.test"
    )
    old_article.published_at = datetime.datetime(2020, 1, 1)
    new_article = await _make_subscribed_article(
        db_session, user, title="New", content="x", url="https://d2.example.test"
    )
    new_article.published_at = datetime.datetime(2026, 1, 1)
    await db_session.commit()

    expr = search_service.parse_search_query("date:2025-01-01..2026-12-31", user.id)
    result = await db_session.execute(
        select(Article).where(expr, Article.id.in_([old_article.id, new_article.id]))
    )
    assert {a.title for a in result.scalars().all()} == {"New"}


@pytest.mark.asyncio
async def test_folder_category_operator(db_session):
    user = await _make_user(db_session)
    folder = Folder(user_id=user.id, name="Tech News")
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)

    source = Source(url="https://c1.example.test", next_fetch_at=utcnow())
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    db_session.add(Subscription(user_id=user.id, source_id=source.id, folder_id=folder.id))
    await db_session.commit()

    article = Article(
        source_id=source.id,
        url="https://c1.example.test/a",
        title="Foldered article",
        content="body",
        word_count=1,
        reading_time_minutes=1,
        published_at=utcnow(),
    )
    db_session.add(article)
    await db_session.commit()

    expr = search_service.parse_search_query("c:Tech", user.id)
    result = await db_session.execute(select(Article).where(expr))
    assert {a.title for a in result.scalars().all()} == {"Foldered article"}


def test_invalid_query_raises_syntax_error():
    with pytest.raises(search_service.SearchSyntaxError):
        search_service.parse_search_query("(unclosed", user_id=1)


def test_ranked_fts_query_builder_rejects_field_operators():
    assert search_service.try_build_ranked_fts_query("intitle:foo") is None
    assert search_service.try_build_ranked_fts_query("/regex/") is None


def test_ranked_fts_query_builder_accepts_plain_boolean_terms():
    match_expr = search_service.try_build_ranked_fts_query("alpha AND -beta")
    assert match_expr == '"alpha" AND NOT "beta"'
