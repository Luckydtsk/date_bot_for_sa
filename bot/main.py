import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.db.session import init_db, make_engine, make_session_factory
from bot.handlers import register_handlers
from bot.handlers.errors import register_errors
from bot.middlewares.db import BanMiddleware, DbSessionMiddleware


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
    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config

    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.update.middleware(BanMiddleware())

    register_handlers(dp)
    register_errors(dp)

    logging.info("Бот запущен. Ctrl+C — остановить.")
    try:
        await dp.start_polling(bot, config=config)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
