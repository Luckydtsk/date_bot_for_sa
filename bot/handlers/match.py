from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import texts as t
from bot.keyboards.cleanup import clear_message_keyboard, clear_tracked_keyboards
from bot.keyboards.common import main_menu_kb

router = Router(name="match")


@router.callback_query(F.data == "match:ok")
async def match_ok(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await clear_message_keyboard(callback.message)
    await callback.message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()
