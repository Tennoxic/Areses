from collections.abc import AsyncGenerator

from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.regex_safety import safe_search
from app.db.models import Source

engine = create_async_engine(settings.database_url, echo=False)


def _regexp(pattern: str, value: str | None) -> bool:
    return safe_search(pattern, value)


if engine.dialect.name == "sqlite":

    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_functions(dbapi_connection, connection_record) -> None:
        dbapi_connection.create_function("REGEXP", 2, _regexp)


def is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def reset_fetching_locks() -> None:
    async with async_session_maker() as session:
        await session.execute(update(Source).values(is_fetching=False))
        await session.commit()
