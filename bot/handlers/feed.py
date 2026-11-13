"""Лента: одна анкета на заход. Кнопки внизу меняют её, новую не шлют."""

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.models import Profile
from bot.db.repositories import LikeRepo, MatchRepo, ProfileRepo
from bot.keyboards.common import feed_controls_kb, menu_for
from bot.live_buttons import discard
from bot.services import (
    EMPTY_BY_MODE,
    can_see,
    process_reaction,
    require_profile,
    touch_username,
)
from bot.states.profile import Feed

logger = logging.getLogger(__name__)
router = Router(name="feed")

# Сообщение, на котором держится нижняя панель. Его нельзя стирать, пока человек в анкетах:
# вместе с ним Telegram убирает кнопки.
_feed_keys: dict[int, int] = {}

_FILTERS = {
    t.FEED_ALL: "all",
    t.FEED_LIKED: "liked",
    t.FEED_DISLIKED: "nope",
}


def _filter_mode(text: str | None) -> str | None:
    if not text:
        return None
    if text.startswith(t.FEED_MARK):
        text = text[len(t.FEED_MARK) :]
    return _FILTERS.get(text)


async def _arm_keyboard(message: Message) -> None:
    """Панель только при входе в анкеты, до карточки. На «Мои» и «Все» заново не шлём."""
    previous = _feed_keys.get(message.chat.id)
    sent = await message.answer("\u2060", reply_markup=feed_controls_kb())
    _feed_keys[message.chat.id] = sent.message_id
    if previous and previous != sent.message_id:
        await discard(message.bot, message.chat.id, previous)


async def _ids(session: AsyncSession, viewer: Profile, mode: str) -> list[int]:
    rows = await ProfileRepo(session).list_catalog(viewer, mode)
    return [row.id for row in rows]


def _decision(profile: Profile, like, matched: bool) -> str:
    if matched:
        return t.decision_match(profile)
    if like is None:
        return t.DECISION_NONE
    if like.is_like:
        return t.DECISION_LIKE
    return t.DECISION_NOPE


async def _caption(
    session: AsyncSession,
    viewer: Profile,
    profile: Profile,
    *,
    index: int,
    total: int,
    mode: str,
    note: str = "",
) -> str:
    like = await LikeRepo(session).get(viewer.id, profile.id)
    matched = bool(like and like.is_like and await MatchRepo(session).get(viewer.id, profile.id))
    body = t.feed_caption(
        profile,
        index=index,
        total=total,
        mode=mode,
        decision=_decision(profile, like, matched),
    )
    if note:
        return f"{note}\n\n{body}"
    return body


async def _shift_press(message: Message, state: FSMContext) -> dict:
    """В ленте новое нажатие остаётся, предыдущее стираем. Вне ленты это не вызывается."""
    data = await state.get_data()
    prev = data.get("press_id")
    if prev and int(prev) != message.message_id:
        await discard(message.bot, message.chat.id, int(prev))
    await state.update_data(press_id=message.message_id)
    return data


async def _paint(
    bot: Bot,
    chat_id: int,
    old_id: int | None,
    profile: Profile,
    caption: str,
    *,
    kind: str | None,
) -> int | None:
    """Правит уже открытую анкету. Новое фото — только когда карточки ещё нет.

    На фото нельзя вешать нижнюю клавиатуру: с ней Telegram не даёт править сообщение.
    Пустой текст тоже можно снова сделать фото.
    """
    if old_id:
        media = InputMediaPhoto(media=profile.photo_file_id, caption=caption, parse_mode="HTML")
        try:
            await bot.edit_message_media(chat_id=chat_id, message_id=int(old_id), media=media)
            return int(old_id)
        except TelegramBadRequest as exc:
            if "not modified" in str(exc).lower():
                return int(old_id)
            if kind == "text":
                await discard(bot, chat_id, int(old_id))
            else:
                logger.warning("Анкету не поправил: %s", exc)
                return int(old_id)
    sent = await bot.send_photo(
        chat_id,
        photo=profile.photo_file_id,
        caption=caption,
        parse_mode="HTML",
    )
    return sent.message_id


async def _remember(
    state: FSMContext, *, mode: str, profile_id: int | None, message_id: int | None
) -> None:
    await state.update_data(
        mode=mode,
        profile_id=profile_id,
        card_id=message_id,
        card_kind="photo",
        notice_id=None,
    )


async def _show(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    session: AsyncSession,
    viewer: Profile,
    profile_id: int,
    mode: str,
    *,
    note: str = "",
) -> None:
    data = await state.get_data()
    ids = await _ids(session, viewer, mode)
    if not ids or profile_id not in ids:
        await _empty(bot, chat_id, state, mode, card_id=data.get("card_id"))
        return
    index = ids.index(profile_id)
    profile = await ProfileRepo(session).get_by_id(profile_id)
    if profile is None:
        await _empty(bot, chat_id, state, mode, card_id=data.get("card_id"))
        return
    caption = await _caption(
        session, viewer, profile, index=index + 1, total=len(ids), mode=mode, note=note
    )
    card_id = await _paint(
        bot, chat_id, data.get("card_id"), profile, caption, kind=data.get("card_kind")
    )
    if card_id is None:
        return
    await _remember(state, mode=mode, profile_id=profile.id, message_id=card_id)


async def _empty(bot: Bot, chat_id: int, state: FSMContext, mode: str, *, card_id: int | None) -> None:
    text = EMPTY_BY_MODE.get(mode, t.FEED_EMPTY_ALL)
    data = await state.get_data()
    if card_id and data.get("card_kind") == "text":
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=int(card_id), text=text)
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                logger.warning("Пустую подборку не вписал: %s", exc)
        await state.update_data(
            mode=mode, profile_id=None, card_id=card_id, card_kind="text", notice_id=None
        )
        return
    # У фото нельзя убрать картинку правкой. Стираем его и оставляем только текст.
    if card_id:
        await discard(bot, chat_id, int(card_id))
    sent = await bot.send_message(chat_id, text)
    await state.update_data(
        mode=mode, profile_id=None, card_id=sent.message_id, card_kind="text", notice_id=None
    )


async def open_feed(
    message: Message, session: AsyncSession, config: Config, state: FSMContext
) -> None:
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE, reply_markup=menu_for(message.from_user.id, config))
        return
    await touch_username(session, viewer, message.from_user.username)
    ids = await _ids(session, viewer, "all")
    if not ids:
        text = t.FEED_EMPTY_ALL
        if not viewer.is_active:
            text += f"\n\nТвоя анкета скрыта. Включить — {t.BTN_MY_PROFILE}."
        await state.clear()
        await message.answer(text, reply_markup=menu_for(message.from_user.id, config))
        return
    note = ""
    if not viewer.is_active:
        note = f"Твоя анкета скрыта. Включить — {t.BTN_MY_PROFILE}."
    await state.set_state(Feed.browsing)
    await state.update_data(
        mode="all",
        profile_id=None,
        card_id=None,
        card_kind=None,
        press_id=message.message_id,
        notice_id=None,
    )
    # Панель на отдельном сообщении: на фото её вешать нельзя, фото тогда не правится.
    await _arm_keyboard(message)
    await _show(message.bot, message.chat.id, state, session, viewer, ids[0], "all", note=note)


async def _viewer(session: AsyncSession, message: Message) -> Profile | None:
    return await require_profile(session, message.from_user.id)


@router.message(Feed.browsing, F.text == t.FEED_NEXT)
@router.message(Feed.browsing, F.text == t.BTN_BACK)
async def feed_move(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await _shift_press(message, state)
    viewer = await _viewer(session, message)
    if not viewer:
        await message.answer(t.NO_PROFILE)
        return
    mode = data.get("mode") or "all"
    ids = await _ids(session, viewer, mode)
    if not ids:
        await _empty(message.bot, message.chat.id, state, mode, card_id=data.get("card_id"))
        return
    if len(ids) == 1:
        await _show(
            message.bot,
            message.chat.id,
            state,
            session,
            viewer,
            ids[0],
            mode,
            note=t.FEED_ONLY_ONE,
        )
        return
    current = data.get("profile_id")
    if current not in ids:
        target = ids[0]
    else:
        delta = 1 if message.text == t.FEED_NEXT else -1
        target = ids[(ids.index(current) + delta) % len(ids)]
    await _show(message.bot, message.chat.id, state, session, viewer, target, mode)


@router.message(Feed.browsing, F.text.func(lambda text: _filter_mode(text) is not None))
async def feed_filter(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await _shift_press(message, state)
    viewer = await _viewer(session, message)
    if not viewer:
        await message.answer(t.NO_PROFILE)
        return
    mode = _filter_mode(message.text) or "all"
    ids = await _ids(session, viewer, mode)
    if not ids:
        await _empty(message.bot, message.chat.id, state, mode, card_id=data.get("card_id"))
        return
    await _show(message.bot, message.chat.id, state, session, viewer, ids[0], mode)


@router.message(Feed.browsing, F.text.in_({t.BTN_LIKE, t.BTN_NOPE}))
async def feed_react(message: Message, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    data = await _shift_press(message, state)
    viewer = await _viewer(session, message)
    if not viewer:
        await message.answer(t.NO_PROFILE)
        return
    mode = data.get("mode") or "all"
    profile_id = data.get("profile_id")
    if not profile_id:
        await _empty(bot, message.chat.id, state, "all", card_id=data.get("card_id"))
        return
    target = await ProfileRepo(session).get_by_id(int(profile_id))
    if not can_see(viewer, target) or target is None:
        ids = await _ids(session, viewer, mode)
        if ids:
            await _show(bot, message.chat.id, state, session, viewer, ids[0], mode)
        else:
            await _empty(bot, message.chat.id, state, mode, card_id=data.get("card_id"))
        return

    before = await _ids(session, viewer, mode)
    pos = before.index(target.id) if target.id in before else 0
    is_like = message.text == t.BTN_LIKE
    outcome = await process_reaction(
        bot,
        session,
        viewer,
        target,
        is_like=is_like,
        quiet_for=viewer.telegram_id,
    )
    if outcome.status == "rejected":
        return

    note = ""
    if outcome.matched:
        note = t.TOAST_MATCH
    elif outcome.unmatched:
        note = t.TOAST_UNMATCH

    after = await _ids(session, viewer, mode)
    if target.id in after:
        await _show(bot, message.chat.id, state, session, viewer, target.id, mode, note=note)
    elif after:
        await _show(
            bot,
            message.chat.id,
            state,
            session,
            viewer,
            after[min(pos, len(after) - 1)],
            mode,
            note=note,
        )
    else:
        await _empty(bot, message.chat.id, state, mode, card_id=data.get("card_id"))


@router.message(Feed.browsing, F.text)
async def feed_unknown(message: Message, state: FSMContext) -> None:
    await _shift_press(message, state)


@router.callback_query(F.data.startswith("f:"))
async def old_feed_buttons(callback: CallbackQuery) -> None:
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    try:
        await callback.answer("Листай кнопками внизу.")
    except Exception:
        pass


@router.message(StateFilter(Feed))
async def feed_other(message: Message, state: FSMContext) -> None:
    await _shift_press(message, state)
