from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.db.models import Base


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def make_engine(database_url: str) -> AsyncEngine:
    kwargs: dict = {"echo": False}
    if _is_sqlite(database_url):
        kwargs["connect_args"] = {"timeout": 30}
    else:
        kwargs["pool_pre_ping"] = True

    engine = create_async_engine(database_url, **kwargs)

    if _is_sqlite(database_url):

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _add_feed_message_column(sync_conn) -> None:  # noqa: ANN001
    """Старая база создана без этой колонки. create_all её не добавляет."""
    rows = sync_conn.execute(text("PRAGMA table_info(profiles)")).fetchall()
    if rows and "feed_message_id" not in {row[1] for row in rows}:
        sync_conn.execute(text("ALTER TABLE profiles ADD COLUMN feed_message_id INTEGER"))


async def init_db(engine: AsyncEngine) -> None:
    """Создаёт недостающие таблицы. Существующие строки не трогает и не удаляет."""
    async with engine.begin() as conn:
        if _is_sqlite(str(engine.url)):
            await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
        if _is_sqlite(str(engine.url)):
            await conn.run_sync(_add_feed_message_column)


async def session_generator(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
