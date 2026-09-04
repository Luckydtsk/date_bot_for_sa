from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.repositories import ProfileRepo
from bot.keyboards.cleanup import clear_tracked_keyboards, track_keyboard_message
from bot.keyboards.common import likes_kb, main_menu_kb
from bot.services import process_reaction, require_profile, send_profile_card

router = Router(name="likes")


async def _show_incoming(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE)
        return

    incoming = await ProfileRepo(session).incoming_likes(viewer)
    if not incoming:
        await message.answer(t.LIKES_EMPTY, reply_markup=main_menu_kb())
        return

    profile, _like = incoming[0]
    await state.update_data(likes_current_id=profile.id)
    sent = await send_profile_card(
        message,
        profile,
        reply_markup=likes_kb(profile.id),
        prefix=t.LIKES_HEADER + "\n\n",
    )
    await track_keyboard_message(state, sent)


@router.message(StateFilter(default_state), F.text == t.BTN_LIKES_ME)
async def likes_me(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await _show_incoming(message, session, state)


@router.callback_query(F.data == "likes:menu")
async def likes_menu(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not callback.message:
        await callback.answer()
        return
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.clear()
    await callback.message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("likes:"))
async def likes_action(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer()
        return
    action = parts[1]
    if action == "menu":
        return

    if len(parts) != 3 or action not in {"like", "skip"}:
        await callback.answer()
        return

    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )

    target_id = int(parts[2])
    viewer = await require_profile(session, callback.from_user.id)
    if not viewer:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return

    repo = ProfileRepo(session)
    # Только если человек реально в «входящих» и ответа ещё нет
    if not await repo.has_pending_incoming_like(viewer.id, target_id):
        await callback.answer("Уже обработано", show_alert=True)
        incoming = await repo.incoming_likes(viewer)
        if not incoming:
            await callback.message.answer(t.LIKES_EMPTY, reply_markup=main_menu_kb())
            return
        profile, _ = incoming[0]
        await state.update_data(likes_current_id=profile.id)
        sent = await send_profile_card(
            callback.message,
            profile,
            reply_markup=likes_kb(profile.id),
            prefix=t.LIKES_HEADER + "\n\n",
        )
        await track_keyboard_message(state, sent)
        return

    target = await repo.get_by_id(target_id)
    if not target:
        await callback.answer("Анкета недоступна", show_alert=True)
    else:
        if action == "like":
            await process_reaction(bot, session, viewer, target, is_like=True)
            await callback.answer(t.LIKE_SENT)
        else:
            await process_reaction(bot, session, viewer, target, is_like=False)
            await callback.answer(t.DISLIKE_DONE)

    incoming = await repo.incoming_likes(viewer)
    if not incoming:
        await state.update_data(likes_current_id=None)
        await callback.message.answer(t.LIKES_EMPTY, reply_markup=main_menu_kb())
        return

    profile, _like = incoming[0]
    await state.update_data(likes_current_id=profile.id)
    sent = await send_profile_card(
        callback.message,
        profile,
        reply_markup=likes_kb(profile.id),
        prefix=t.LIKES_HEADER + "\n\n",
    )
    await track_keyboard_message(state, sent)
