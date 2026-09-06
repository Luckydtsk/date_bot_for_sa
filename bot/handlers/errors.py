import logging

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from bot import texts as t

logger = logging.getLogger(__name__)


async def on_error(event: ErrorEvent, bot: Bot) -> None:
    logger.exception("Unhandled error: %s", event.exception)
    update = event.update
    try:
        if update.callback_query:
            try:
                await update.callback_query.answer(
                    "Что-то сломалось, попробуй ещё раз", show_alert=True
                )
            except Exception:
                pass
        elif update.message:
            await update.message.answer(t.UNKNOWN)
    except Exception:
        logger.exception("Failed to notify user about error")


def register_errors(dp: Dispatcher) -> None:
    dp.errors.register(on_error)
