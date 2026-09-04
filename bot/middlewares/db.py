from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Update, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot import texts as t
from bot.config import Config
from bot.db.repositories import ProfileRepo


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")
        if not user or not session:
            return await handler(event, data)

        config: Config | None = data.get("config")
        is_admin = bool(config and user.id in config.admin_ids)

        # Админ-команды пропускаем только для реальных админов
        if is_admin and isinstance(event, Update) and event.message and event.message.text:
            cmd = event.message.text.split()[0].split("@")[0]
            if cmd in {"/stats", "/broadcast", "/ban", "/unban"}:
                return await handler(event, data)

        profile = await ProfileRepo(session).get_by_tg(user.id)
        if not (profile and profile.is_banned):
            return await handler(event, data)

        bot: Bot | None = data.get("bot")
        if isinstance(event, Update) and event.callback_query:
            await event.callback_query.answer(t.PROFILE_BANNED, show_alert=True)
        elif isinstance(event, Update) and event.message:
            await event.message.answer(t.PROFILE_BANNED)
        elif bot:
            try:
                await bot.send_message(user.id, t.PROFILE_BANNED)
            except Exception:
                pass
        return None
