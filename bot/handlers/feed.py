from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.models import Profile
from bot.db.repositories import LikeRepo, ProfileRepo
from bot.keyboards.cleanup import clear_tracked_keyboards, track_keyboard_message
from bot.config import Config
from bot.keyboards.common import feed_kb, menu_for
from bot.services import process_reaction, require_profile, send_profile_card

router = Router(name="feed")


async def _show_catalog_card(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    viewer: Profile,
    config: Config,
    *,
    index: int,
) -> None:
    data = await state.get_data()
    ids: list[int] = list(data.get("feed_ids") or [])
    if not ids:
        await message.answer(t.FEED_EMPTY, reply_markup=menu_for(message.from_user.id, config))
        return

    index = index % len(ids)
    profile = await ProfileRepo(session).get_by_id(ids[index])
    if profile is None or not profile.is_complete or profile.is_banned or not profile.is_active:
        # Анкета пропала — перезагрузим каталог
        catalog = await ProfileRepo(session).list_catalog(viewer)
        if not catalog:
            await state.clear()
            await message.answer(t.FEED_EMPTY, reply_markup=menu_for(message.from_user.id, config))
            return
        ids = [p.id for p in catalog]
        index = min(index, len(ids) - 1)
        profile = catalog[index]
        await state.update_data(feed_ids=ids)

    liked = await LikeRepo(session).get(viewer.id, profile.id)
    already = bool(liked and liked.is_like)
    prefix = t.FEED_CARD_PREFIX.format(index=index + 1, total=len(ids))
    if already:
        prefix += f"\n{t.FEED_ALREADY_LIKED}"
    prefix += "\n\n"

    await state.update_data(feed_index=index, feed_current_id=profile.id)
    sent = await send_profile_card(
        message,
        profile,
        reply_markup=feed_kb(profile.id, index=index, total=len(ids)),
        prefix=prefix,
    )
    await track_keyboard_message(state, sent)


@router.message(StateFilter(default_state), F.text == t.BTN_BROWSE)
async def browse(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
) -> None:
    await start_browse(message, state, session, bot, config)


async def start_browse(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE, reply_markup=menu_for(message.from_user.id, config))
        return

    if not viewer.is_active:
        await message.answer(t.FEED_PAUSED_HINT)

    catalog = await ProfileRepo(session).list_catalog(viewer)
    if not catalog:
        await message.answer(t.FEED_EMPTY, reply_markup=menu_for(message.from_user.id, config))
        return

    await message.answer(t.FEED_COUNT.format(n=len(catalog)), reply_markup=menu_for(message.from_user.id, config))
    await state.update_data(feed_ids=[p.id for p in catalog], feed_index=0)
    await _show_catalog_card(message, state, session, viewer, config, index=0)


async def _move(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
    *,
    delta: int,
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
    ids: list[int] = list(data.get("feed_ids") or [])
    if not ids:
        # Обновим каталог на лету
        catalog = await ProfileRepo(session).list_catalog(viewer)
        if not catalog:
            await callback.message.answer(t.FEED_EMPTY, reply_markup=menu_for(callback.from_user.id, config))
            await callback.answer()
            return
        ids = [p.id for p in catalog]
        await state.update_data(feed_ids=ids)
        index = 0
    else:
        index = int(data.get("feed_index", 0)) + delta

    await callback.answer()
    await _show_catalog_card(callback.message, state, session, viewer, config, index=index)


@router.callback_query(F.data.startswith("feed:prev:"))
async def feed_prev(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
) -> None:
    await _move(callback, state, session, bot, config, delta=-1)


@router.callback_query(F.data.startswith("feed:next:"))
async def feed_next(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
) -> None:
    await _move(callback, state, session, bot, config, delta=1)


@router.callback_query(F.data.startswith("feed:like:"))
async def feed_like(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
) -> None:
    if not callback.message:
        await callback.answer()
        return

    target_id = int(callback.data.split(":")[-1])
    viewer = await require_profile(session, callback.from_user.id)
    if not viewer:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return

    data = await state.get_data()
    current_id = data.get("feed_current_id")
    if current_id is not None and int(current_id) != target_id:
        await callback.answer("Открой ленту заново", show_alert=True)
        return

    target = await ProfileRepo(session).get_by_id(target_id)
    if target is None:
        await callback.answer("Анкета недоступна", show_alert=True)
        return

    existing = await LikeRepo(session).get(viewer.id, target.id)
    if existing and existing.is_like:
        await callback.answer(t.LIKE_ALREADY, show_alert=True)
        return

    await process_reaction(bot, session, viewer, target, is_like=True)
    await callback.answer(t.LIKE_SENT)

    # Остаёмся на той же анкете, обновляем пометку «уже лайкнул»
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    index = int(data.get("feed_index", 0))
    await _show_catalog_card(callback.message, state, session, viewer, config, index=index)


@router.callback_query(F.data == "feed:noop")
async def feed_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.in_({"feed:like", "feed:dislike"}))
@router.callback_query(F.data.startswith("feed:dislike:"))
async def feed_legacy(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if callback.message:
        await clear_tracked_keyboards(
            bot, callback.message.chat.id, state, also=callback.message
        )
    await callback.answer("Кнопка устарела — открой «Смотреть анкеты»", show_alert=True)


@router.callback_query(F.data == "feed:sleep")
async def feed_sleep(callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config) -> None:
    if not callback.message:
        await callback.answer()
        return
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.clear()
    await callback.message.answer(
        t.MENU_TITLE, reply_markup=menu_for(callback.from_user.id, config)
    )
    await callback.answer()
