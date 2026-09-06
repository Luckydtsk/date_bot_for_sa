import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.db.session import init_db, make_engine, make_session_factory
from bot.handlers import register_handlers
from bot.handlers.errors import register_errors
from bot.middlewares.db import BanMiddleware, DbSessionMiddleware


def _make_storage(redis_url: str | None):
    if not redis_url:
        return MemoryStorage()
    try:
        from aiogram.fsm.storage.redis import RedisStorage

        return RedisStorage.from_url(redis_url)
    except Exception:
        logging.getLogger(__name__).exception(
            "REDIS_URL задан, но RedisStorage не поднялся — fallback MemoryStorage"
        )
        return MemoryStorage()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()

    engine = make_engine(config.database_url)
    session_factory = make_session_factory(engine)
    await init_db(engine)

    # Без parse_mode по умолчанию — в анкетах бывают символы < > &
    bot = Bot(token=config.bot_token)
    storage = _make_storage(config.redis_url)
    dp = Dispatcher(storage=storage)
    dp["config"] = config

    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.update.middleware(BanMiddleware())

    register_handlers(dp)
    register_errors(dp)

    logging.info(
        "Бот запущен (FSM: %s). Ctrl+C — остановить.",
        type(storage).__name__,
    )
    try:
        await dp.start_polling(bot, config=config)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
