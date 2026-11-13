from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="match")


@router.callback_query(F.data == "match:ok")
async def match_ok(callback: CallbackQuery) -> None:
    """Старые сообщения с кнопкой «Круто»."""
    await callback.answer("Меню внизу. Пара на месте.")
