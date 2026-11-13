from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot import texts as t
from bot.config import Config
from bot.keyboards.common import menu_for
from bot.services import require_profile

router = Router(name="fallback")


@router.message(StateFilter(default_state), F.text)
async def unknown_text(message: Message, session, config: Config) -> None:
    profile = await require_profile(session, message.from_user.id)
    markup = menu_for(message.from_user.id, config) if profile else None
    await message.answer(t.UNKNOWN, reply_markup=markup)


@router.message(StateFilter(default_state))
async def unknown_other(message: Message) -> None:
    await message.answer(t.UNKNOWN)
