from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot import texts as t
from bot.config import Config
from bot.keyboards.common import menu_for

router = Router(name="fallback")


@router.message(StateFilter(default_state), F.text)
async def unknown_text(message: Message, config: Config) -> None:
    await message.answer(t.UNKNOWN, reply_markup=menu_for(message.from_user.id, config))
