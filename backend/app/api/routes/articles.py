from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db.models import Article, Subscription, User, UserArticleState
from app.db.session import get_session, is_sqlite
from app.schemas.articles import (
    ArticleDetailOut,
    ArticleOut,
    MarkAllReadRequest,
    ReadLaterToggleOut,
    ScrollPositionUpdate,
    StarToggleOut,
    TranslateOut,
    TranslateRequest,
)
from app.services import ai_summary, read_state, search_service

router = APIRouter(prefix="/api/articles", tags=["articles"])

_DEFAULT_LIMIT = 30
_MAX_LIMIT = 100


def _to_out(article: Article, state: UserArticleState | None) -> dict:
    return {
        "id": article.id,
        "source_id": article.source_id,
        "url": article.url,
        "title": article.title,
        "ai_summary": article.ai_summary,
        "word_count": article.word_count,
        "reading_time_minutes": article.reading_time_minutes,
        "published_at": article.published_at,
        "fetched_at": article.fetched_at,
        "is_read": state.is_read if state else False,
        "starred": state.starred if state else False,
        "read_later": state.read_later if state else False,
        "scroll_position": state.scroll_position if state else 0.0,
        "enclosure_url": article.enclosure_url,
        "enclosure_type": article.enclosure_type,
        "extraction_failed": article.extraction_failed,
    }


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    source_id: int | None = Query(default=None, alias="sourceId"),
    folder_id: int | None = Query(default=None, alias="folderId"),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    starred_only: bool = Query(default=False, alias="starredOnly"),
    read_later_only: bool = Query(default=False, alias="readLaterOnly"),
    has_summary_only: bool = Query(default=False, alias="hasSummaryOnly"),
    q: str | None = None,
    before_id: int | None = Query(default=None, alias="beforeId"),
    limit: int = _DEFAULT_LIMIT,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    limit = min(limit, _MAX_LIMIT)

    stmt = (
        select(Article, UserArticleState)
        .join(
            Subscription,
            (Subscription.source_id == Article.source_id)
            & (Subscription.user_id == user.id),
        )
        .outerjoin(
            UserArticleState,
            (UserArticleState.article_id == Article.id)
            & (UserArticleState.user_id == user.id),
        )
    )

    if source_id is not None:
        stmt = stmt.where(Article.source_id == source_id)
    if folder_id is not None:
        stmt = stmt.where(Subscription.folder_id == folder_id)
    if source_id is None and folder_id is None:
        stmt = stmt.where(Subscription.hidden.is_(False))
    if unread_only:
        stmt = stmt.where(
            (UserArticleState.is_read.is_(False)) | (UserArticleState.is_read.is_(None))
        )
    if starred_only:
        stmt = stmt.where(UserArticleState.starred.is_(True))
    if read_later_only:
        stmt = stmt.where(UserArticleState.read_later.is_(True))
    if has_summary_only:
        stmt = stmt.where(Article.ai_summary.is_not(None))
    if before_id is not None:
        stmt = stmt.where(Article.id < before_id)

    rank_column = None
    if q:
        if not is_sqlite():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={
                    "code": "fts_unavailable",
                    "message": (
                        "Full-text search (f:/intitle:/regex/etc.) requires SQLite. "
                        "This deployment is running on a non-SQLite database, where "
                        "FTS5 and REGEXP are unavailable."
                    ),
                },
            )
        ranked_match = search_service.try_build_ranked_fts_query(q)
        if ranked_match is not None:
            from sqlalchemy import text as _text

            rank_subquery = (
                _text(
                    "SELECT rowid AS article_id, bm25(articles_fts) AS rank "
                    "FROM articles_fts WHERE articles_fts MATCH :fts_q"
                )
                .bindparams(fts_q=ranked_match)
                .columns(article_id=Integer, rank=Float)
                .subquery()
            )
            stmt = stmt.join(rank_subquery, rank_subquery.c.article_id == Article.id)
            rank_column = rank_subquery.c.rank
        else:
            try:
                search_expr = search_service.parse_search_query(q, user.id)
            except search_service.SearchSyntaxError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "invalid_search_query", "message": str(exc)},
                ) from exc
            if search_expr is not None:
                stmt = stmt.where(search_expr)

    if rank_column is not None:
        stmt = stmt.order_by(rank_column.asc(), Article.id.desc()).limit(limit)
    else:
        stmt = stmt.order_by(Article.id.desc()).limit(limit)

    result = await session.execute(stmt)
    return [_to_out(article, state) for article, state in result.all()]


@router.get("/{article_id}", response_model=ArticleDetailOut)
async def get_article(
    article_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = (
        select(Article, UserArticleState)
        .join(
            Subscription,
            (Subscription.source_id == Article.source_id)
            & (Subscription.user_id == user.id),
        )
        .outerjoin(
            UserArticleState,
            (UserArticleState.article_id == Article.id)
            & (UserArticleState.user_id == user.id),
        )
        .where(Article.id == article_id)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    article, state = row
    out = _to_out(article, state)
    out["content"] = article.content
    return out


async def _require_article_access(session: AsyncSession, user_id: int, article_id: int) -> None:
    if not await read_state.user_can_access_article(session, user_id, article_id):
        raise HTTPException(
            status_code=404,
            detail={"code": "article_not_found", "message": "article not found"},
        )


@router.post("/{article_id}/read")
async def mark_read_route(
    article_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _require_article_access(session, user.id, article_id)
    await read_state.mark_read(session, user.id, article_id)
    return {"status": "ok"}


@router.post("/{article_id}/unread")
async def mark_unread_route(
    article_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _require_article_access(session, user.id, article_id)
    await read_state.mark_unread(session, user.id, article_id)
    return {"status": "ok"}


@router.post("/{article_id}/star", response_model=StarToggleOut)
async def toggle_star_route(
    article_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> StarToggleOut:
    await _require_article_access(session, user.id, article_id)
    starred = await read_state.toggle_star(session, user.id, article_id)
    return StarToggleOut(starred=starred)


@router.post("/{article_id}/read-later", response_model=ReadLaterToggleOut)
async def toggle_read_later_route(
    article_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> ReadLaterToggleOut:
    await _require_article_access(session, user.id, article_id)
    read_later = await read_state.toggle_read_later(session, user.id, article_id)
    return ReadLaterToggleOut(read_later=read_later)


@router.post("/{article_id}/scroll-position")
async def scroll_position_route(
    article_id: int,
    body: ScrollPositionUpdate,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _require_article_access(session, user.id, article_id)
    await read_state.update_scroll_position(session, user.id, article_id, body.position)
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read_route(
    body: MarkAllReadRequest,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await read_state.mark_all_read(session, user.id, body.source_id, body.folder_id)
    return {"status": "ok"}


@router.post("/{article_id}/generate-summary", response_model=ArticleDetailOut)
async def generate_summary_route(
    article_id: int,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _require_article_access(session, user.id, article_id)
    article = await ai_summary.generate_summary_now(session, article_id)
    state_result = await session.execute(
        select(UserArticleState).where(
            UserArticleState.article_id == article_id,
            UserArticleState.user_id == user.id,
        )
    )
    state = state_result.scalar_one_or_none()
    out = _to_out(article, state)
    out["content"] = article.content
    return out


@router.post("/{article_id}/translate", response_model=TranslateOut)
async def translate_article_route(
    article_id: int,
    body: TranslateRequest,
    user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> TranslateOut:
    await _require_article_access(session, user.id, article_id)
    translated = await ai_summary.translate_article(session, article_id, body.target_language)
    return TranslateOut(translated_content=translated)
