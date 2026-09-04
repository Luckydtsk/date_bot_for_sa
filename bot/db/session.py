from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.models import Base


def make_engine(database_url: str):
    return create_async_engine(database_url, echo=False)


def make_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine) -> None:
    """Создаёт таблицы, если их ещё нет (схема описана в models.py)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session_generator(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
