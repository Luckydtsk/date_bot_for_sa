from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.db.models import Base


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def make_engine(database_url: str) -> AsyncEngine:
    kwargs: dict = {"echo": False}
    if _is_sqlite(database_url):
        # Для локальной разработки
        pass
    else:
        # Postgres на Railway / проде
        kwargs["pool_pre_ping"] = True

    engine = create_async_engine(database_url, **kwargs)

    if _is_sqlite(database_url):

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """Создаёт таблицы, если их ещё нет (схема описана в models.py)."""
    async with engine.begin() as conn:
        if _is_sqlite(str(engine.url)):
            await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)


async def session_generator(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
