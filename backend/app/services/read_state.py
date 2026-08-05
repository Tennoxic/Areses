import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.db.models import (
    Article,
    PasswordResetToken,
    Subscription,
    UserArticleState,
    UserSession,
)

_DEFAULT_RETENTION_DAYS = 30


async def user_can_access_article(
    session: AsyncSession, user_id: int, article_id: int
) -> bool:
    result = await session.execute(
        select(Article.id)
        .join(Subscription, Subscription.source_id == Article.source_id)
        .where(Article.id == article_id, Subscription.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


async def _get_state(
    session: AsyncSession, user_id: int, article_id: int
) -> UserArticleState:
    result = await session.execute(
        select(UserArticleState).where(
            UserArticleState.user_id == user_id,
            UserArticleState.article_id == article_id,
        )
    )
    state = result.scalar_one_or_none()
    if state is None:
        state = UserArticleState(user_id=user_id, article_id=article_id)
        session.add(state)
    return state


async def mark_read(session: AsyncSession, user_id: int, article_id: int) -> None:
    state = await _get_state(session, user_id, article_id)
    state.is_read = True
    state.read_at = utcnow()
    await session.commit()


async def mark_unread(session: AsyncSession, user_id: int, article_id: int) -> None:
    state = await _get_state(session, user_id, article_id)
    state.is_read = False
    state.read_at = None
    await session.commit()


async def toggle_star(session: AsyncSession, user_id: int, article_id: int) -> bool:
    state = await _get_state(session, user_id, article_id)
    state.starred = not state.starred
    await session.commit()
    return state.starred


async def toggle_read_later(session: AsyncSession, user_id: int, article_id: int) -> bool:
    state = await _get_state(session, user_id, article_id)
    state.read_later = not state.read_later
    await session.commit()
    return state.read_later


async def mark_all_read(
    session: AsyncSession,
    user_id: int,
    source_id: int | None = None,
    folder_id: int | None = None,
) -> None:
    now = utcnow()

    subquery = (
        select(Article.id)
        .join(Subscription, Subscription.source_id == Article.source_id)
        .where(Subscription.user_id == user_id)
    )
    if source_id is not None:
        subquery = subquery.where(Article.source_id == source_id)
    if folder_id is not None:
        subquery = subquery.where(Subscription.folder_id == folder_id)

    result = await session.execute(subquery)
    article_ids = [row[0] for row in result.all()]
    if not article_ids:
        return

    existing_result = await session.execute(
        select(UserArticleState.article_id).where(
            UserArticleState.user_id == user_id,
            UserArticleState.article_id.in_(article_ids),
        )
    )
    existing_ids = {row[0] for row in existing_result.all()}

    await session.execute(
        update(UserArticleState)
        .where(
            UserArticleState.user_id == user_id,
            UserArticleState.article_id.in_(existing_ids),
        )
        .values(is_read=True, read_at=now)
    )

    new_ids = [aid for aid in article_ids if aid not in existing_ids]
    session.add_all(
        [
            UserArticleState(
                user_id=user_id, article_id=aid, is_read=True, read_at=now
            )
            for aid in new_ids
        ]
    )
    await session.commit()


async def update_scroll_position(
    session: AsyncSession, user_id: int, article_id: int, position: float
) -> None:
    state = await _get_state(session, user_id, article_id)
    state.scroll_position = position
    await session.commit()


async def get_unread_counts(session: AsyncSession, user_id: int) -> dict[int, int]:
    result = await session.execute(
        select(Subscription.source_id, func.count(Article.id))
        .select_from(Subscription)
        .join(Article, Article.source_id == Subscription.source_id)
        .outerjoin(
            UserArticleState,
            (UserArticleState.article_id == Article.id)
            & (UserArticleState.user_id == user_id),
        )
        .where(
            Subscription.user_id == user_id,
            (UserArticleState.is_read.is_(False))
            | (UserArticleState.is_read.is_(None)),
        )
        .group_by(Subscription.source_id)
    )
    return {source_id: count for source_id, count in result.all()}


async def run_retention_cleanup(session: AsyncSession) -> int:
    cutoff = utcnow() - datetime.timedelta(
        days=_DEFAULT_RETENTION_DAYS
    )

    single_subscriber_sources = (
        select(Subscription.source_id)
        .group_by(Subscription.source_id)
        .having(func.count(Subscription.id) == 1)
    )

    starred_article_ids = select(UserArticleState.article_id).where(
        UserArticleState.starred.is_(True)
    )

    eligible_article_ids = select(UserArticleState.article_id).where(
        UserArticleState.is_read.is_(True),
        UserArticleState.starred.is_(False),
        UserArticleState.read_at < cutoff,
    )

    deletable = select(Article.id).where(
        Article.source_id.in_(single_subscriber_sources),
        Article.id.in_(eligible_article_ids),
        Article.id.not_in(starred_article_ids),
    )

    result = await session.execute(deletable)
    article_ids = [row[0] for row in result.all()]

    if article_ids:
        await session.execute(
            delete(UserArticleState).where(
                UserArticleState.article_id.in_(article_ids)
            )
        )
        await session.execute(delete(Article).where(Article.id.in_(article_ids)))

    now = utcnow()
    await session.execute(delete(UserSession).where(UserSession.expires_at < now))
    await session.execute(
        delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
    )

    await session.commit()
    return len(article_ids)
