import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from bot.config import load_config, safe_db_label
from bot.db.repositories import ProfileRepo
from bot.db.session import init_db, make_engine, make_session_factory
from bot.handlers import register_handlers
from bot.handlers.errors import register_errors
from bot.live_buttons import ClearButtonsMiddleware
from bot.middlewares.db import BanMiddleware, DbSessionMiddleware

logger = logging.getLogger(__name__)

USER_COMMANDS = [
    BotCommand(command="start", description="Меню или начать анкету"),
    BotCommand(command="help", description="Какая кнопка за что отвечает"),
    BotCommand(command="cancel", description="Отменить текущий шаг"),
]
ADMIN_COMMANDS = USER_COMMANDS + [
    BotCommand(command="admin", description="Админка"),
    BotCommand(command="stats", description="Статистика"),
    BotCommand(command="users", description="Список анкет"),
    BotCommand(command="broadcast", description="Рассылка"),
    BotCommand(command="log", description="Лайки, дизлайки и пары"),
    BotCommand(command="notify", description="Toggle alerts"),
]


def _make_storage(redis_url: str | None):
    if not redis_url:
        return MemoryStorage()
    try:
        from aiogram.fsm.storage.redis import RedisStorage

        return RedisStorage.from_url(redis_url)
    except Exception:
        logger.exception("Redis не поднялся, состояния будут в памяти")
        return MemoryStorage()


async def _setup_commands(bot: Bot, admin_ids: frozenset[int]) -> None:
    """Меню со / видно только админу. У остальных список команд пустой.

    «Старт» в чате всё равно открывает бота: Telegram шлёт /start сам.
    """
    for scope in (
        BotCommandScopeDefault(),
        BotCommandScopeAllPrivateChats(),
        BotCommandScopeAllGroupChats(),
    ):
        try:
            await bot.delete_my_commands(scope=scope)
        except Exception:
            logger.info("Не удалось очистить общее меню команд")
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception:
            logger.info("Команды админа не записались для %s", admin_id)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()
    engine = make_engine(config.database_url)
    session_factory = make_session_factory(engine)
    await init_db(engine)
    async with session_factory() as session:
        stored = await ProfileRepo(session).count_complete()
    logger.info(
        "База на месте (%s), анкет: %s. Перезапуск данные не стирает.",
        safe_db_label(config.database_url),
        stored,
    )

    bot = Bot(token=config.bot_token)
    storage = _make_storage(config.redis_url)
    dp = Dispatcher(storage=storage)
    dp["config"] = config
    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.update.middleware(BanMiddleware())
    dp.message.middleware(ClearButtonsMiddleware())
    dp.callback_query.middleware(ClearButtonsMiddleware())
    register_handlers(dp)
    register_errors(dp)
    await _setup_commands(bot, config.admin_ids)

    logger.info("Бот запущен (состояния: %s). Ctrl+C — остановить.", type(storage).__name__)
    try:
        await dp.start_polling(bot, config=config)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
