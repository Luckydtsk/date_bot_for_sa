from aiogram import Dispatcher, Router

from bot.handlers import admin, fallback, feed, likes, match, profile, start


def setup_routers() -> Router:
    root = Router()
    root.include_router(admin.router)
    root.include_router(start.router)
    root.include_router(profile.router)
    root.include_router(feed.router)
    root.include_router(likes.router)
    root.include_router(match.router)
    # fallback — последним
    root.include_router(fallback.router)
    return root


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(setup_routers())
