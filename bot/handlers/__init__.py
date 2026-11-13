from aiogram import Dispatcher, Router

from bot.handlers import admin, fallback, feed, likes, match, navigation, profile, register


def setup_routers() -> Router:
    root = Router()
    # Меню и отмена — первыми, чтобы сработать даже посреди анкеты.
    root.include_router(navigation.router)
    root.include_router(register.router)
    root.include_router(profile.router)
    root.include_router(feed.router)
    root.include_router(likes.router)
    root.include_router(admin.router)
    root.include_router(match.router)
    root.include_router(fallback.router)
    return root


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(setup_routers())
