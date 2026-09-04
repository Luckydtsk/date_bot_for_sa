from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.repositories import ProfileRepo
from bot.keyboards.cleanup import clear_tracked_keyboards, track_keyboard_message
from bot.keyboards.common import feed_kb, main_menu_kb
from bot.services import process_reaction, require_profile, send_profile_card

router = Router(name="feed")


@router.message(StateFilter(default_state), F.text == t.BTN_BROWSE)
async def browse(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE)
        return

    if not viewer.is_active:
        await message.answer(t.FEED_PAUSED_HINT)

    candidate = await ProfileRepo(session).next_feed_candidate(viewer)
    if not candidate:
        await message.answer(t.FEED_EMPTY, reply_markup=main_menu_kb())
        return

    await state.update_data(feed_current_id=candidate.id)
    sent = await send_profile_card(message, candidate, reply_markup=feed_kb())
    await track_keyboard_message(state, sent)


async def _react_and_next(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    *,
    is_like: bool,
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )

    data = await state.get_data()
    current_id = data.get("feed_current_id")
    viewer = await require_profile(session, callback.from_user.id)
    if not viewer:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    if not current_id:
        await callback.answer(t.FEED_EMPTY, show_alert=True)
        await callback.message.answer(t.FEED_EMPTY, reply_markup=main_menu_kb())
        return

    target = await ProfileRepo(session).get_by_id(int(current_id))
    if not target:
        await callback.answer("Анкета уже недоступна", show_alert=True)
    else:
        await process_reaction(bot, session, viewer, target, is_like=is_like)
        await callback.answer(t.LIKE_SENT if is_like else t.DISLIKE_DONE)

    candidate = await ProfileRepo(session).next_feed_candidate(viewer)
    if not candidate:
        await state.update_data(feed_current_id=None)
        await callback.message.answer(t.FEED_EMPTY, reply_markup=main_menu_kb())
        return

    await state.update_data(feed_current_id=candidate.id)
    sent = await send_profile_card(callback.message, candidate, reply_markup=feed_kb())
    await track_keyboard_message(state, sent)


@router.callback_query(F.data == "feed:like")
async def feed_like(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await _react_and_next(callback, state, session, bot, is_like=True)


@router.callback_query(F.data == "feed:dislike")
async def feed_dislike(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await _react_and_next(callback, state, session, bot, is_like=False)


@router.callback_query(F.data == "feed:sleep")
async def feed_sleep(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.clear()
    await callback.message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()
