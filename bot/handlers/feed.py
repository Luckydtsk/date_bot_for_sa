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
    sent = await send_profile_card(
        message, candidate, reply_markup=feed_kb(candidate.id)
    )
    await track_keyboard_message(state, sent)


async def _react_and_next(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    *,
    target_id: int,
    is_like: bool,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )

    viewer = await require_profile(session, callback.from_user.id)
    if not viewer:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return

    data = await state.get_data()
    current_id = data.get("feed_current_id")
    # Старые кнопки без id в data или чужой id — игнор
    if current_id is not None and int(current_id) != target_id:
        await callback.answer("Анкету уже пролистали", show_alert=True)
        return

    target = await ProfileRepo(session).get_by_id(target_id)
    if target is None:
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
    sent = await send_profile_card(
        callback.message, candidate, reply_markup=feed_kb(candidate.id)
    )
    await track_keyboard_message(state, sent)


@router.callback_query(F.data.startswith("feed:like:"))
async def feed_like(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    target_id = int(callback.data.split(":")[-1])
    await _react_and_next(
        callback, state, session, bot, target_id=target_id, is_like=True
    )


@router.callback_query(F.data.startswith("feed:dislike:"))
async def feed_dislike(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    target_id = int(callback.data.split(":")[-1])
    await _react_and_next(
        callback, state, session, bot, target_id=target_id, is_like=False
    )


# Старые кнопки без profile_id — просто гасим
@router.callback_query(F.data.in_({"feed:like", "feed:dislike"}))
async def feed_legacy(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if callback.message:
        await clear_tracked_keyboards(
            bot, callback.message.chat.id, state, also=callback.message
        )
    await callback.answer("Кнопка устарела — открой ленту заново", show_alert=True)


@router.callback_query(F.data == "feed:sleep")
async def feed_sleep(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not callback.message:
        await callback.answer()
        return
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.clear()
    await callback.message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()
