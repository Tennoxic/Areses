import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, Subscription
from app.services import settings_service
from app.services.providers.client import get_model_response
from app.services.sanitizer import strip_tags

_logger = logging.getLogger(__name__)

_DEFAULT_CONTENT_LIMIT_WORDS = 1000

_PROMPT_TEMPLATE = (
    "Summarize the following article in 2-3 concise sentences, "
    "capturing the key facts only:\n\n{content}"
)


async def _has_summarize_subscriber(session: AsyncSession, source_id: int) -> bool:
    result = await session.execute(
        select(Subscription.id).where(
            Subscription.source_id == source_id,
            Subscription.summarize_enabled.is_(True),
        )
    )
    return result.first() is not None


async def maybe_enqueue_summary(session: AsyncSession, article: Article) -> None:
    if not article.content:
        return
    if await _has_summarize_subscriber(session, article.source_id):
        await session.execute(
            update(Article).where(Article.id == article.id).values(summary_pending=True)
        )
        await session.commit()


async def _get_provider_config(session: AsyncSession) -> dict:
    return {
        "provider": await settings_service.get_global_setting(
            session, "aiProvider", "anthropic"
        ),
        "model": await settings_service.get_global_setting(
            session, "aiModel", "claude-sonnet-5"
        ),
        "api_key": await settings_service.get_global_setting(session, "aiApiKey"),
        "baseUrl": await settings_service.get_global_setting(session, "aiBaseUrl"),
        "contentLimit": int(
            await settings_service.get_global_setting(
                session, "contentLimit", str(_DEFAULT_CONTENT_LIMIT_WORDS)
            )
        ),
    }


async def _summarize_article(
    session: AsyncSession, article_id: int, content: str | None
) -> None:
    if not content:
        await session.execute(
            update(Article)
            .where(Article.id == article_id)
            .values(summary_pending=False)
        )
        await session.commit()
        return
    config = await _get_provider_config(session)
    plain_text = strip_tags(content)
    truncated = " ".join(plain_text.split()[: config["contentLimit"]])
    prompt = _PROMPT_TEMPLATE.format(content=truncated)
    try:
        summary = await get_model_response(
            config["provider"],
            config["model"],
            prompt,
            config["api_key"],
            config["baseUrl"],
        )
        await session.execute(
            update(Article)
            .where(Article.id == article_id)
            .values(ai_summary=summary, summary_pending=False)
        )
    except Exception:
        _logger.exception("failed to generate AI summary for article %s", article_id)
        await session.execute(
            update(Article)
            .where(Article.id == article_id)
            .values(summary_pending=False)
        )
    await session.commit()


async def process_pending_summaries(session: AsyncSession) -> int:
    result = await session.execute(
        select(Article.id, Article.content).where(Article.summary_pending.is_(True))
    )
    pending = result.all()
    for article_id, content in pending:
        await _summarize_article(session, article_id, content)
    return len(pending)


_TRANSLATE_PROMPT_TEMPLATE = (
    "Translate the following article into {language}. "
    "Preserve the meaning and tone, output only the translated text "
    "with no preamble or explanation:\n\n{content}"
)


async def translate_article(
    session: AsyncSession, article_id: int, target_language: str
) -> str:
    result = await session.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one()
    config = await _get_provider_config(session)
    plain_text = strip_tags(article.content or "")
    truncated = " ".join(plain_text.split()[: config["contentLimit"]])
    prompt = _TRANSLATE_PROMPT_TEMPLATE.format(language=target_language, content=truncated)
    return await get_model_response(
        config["provider"],
        config["model"],
        prompt,
        config["api_key"],
        config["baseUrl"],
    )


async def generate_summary_now(session: AsyncSession, article_id: int) -> Article:
    result = await session.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one()
    await _summarize_article(session, article_id, article.content)
    await session.refresh(article)
    return article
