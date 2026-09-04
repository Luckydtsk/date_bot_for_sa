from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot import texts as t
from bot.keyboards.common import main_menu_kb

router = Router(name="fallback")


@router.message(StateFilter(default_state), F.text)
async def unknown_text(message: Message) -> None:
    await message.answer(t.UNKNOWN, reply_markup=main_menu_kb())
