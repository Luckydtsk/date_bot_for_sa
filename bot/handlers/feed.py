"""Лента: все анкеты по кругу, решение можно поменять."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.models import Profile
from bot.db.repositories import LikeRepo, MatchRepo, ProfileRepo
from bot.keyboards.common import feed_filters_kb, feed_kb, menu_for
from bot.services import (
    EMPTY_BY_MODE,
    MODE_BY_CODE,
    can_see,
    deliver_photo,
    process_reaction,
    require_profile,
    touch_username,
)

router = Router(name="feed")


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


async def _show(
    message: Message,
    session: AsyncSession,
    viewer: Profile,
    profile_id: int,
    mode: str,
    *,
    edit: bool,
) -> None:
    ids = await _ids(session, viewer, mode)
    if not ids or profile_id not in ids:
        await _empty(message, mode, edit=edit)
        return
    index = ids.index(profile_id)
    profile = await ProfileRepo(session).get_by_id(profile_id)
    if profile is None:
        await _empty(message, mode, edit=edit)
        return
    like = await LikeRepo(session).get(viewer.id, profile.id)
    matched = bool(like and like.is_like and await MatchRepo(session).get(viewer.id, profile.id))
    caption = t.feed_caption(
        profile,
        index=index + 1,
        total=len(ids),
        mode=mode,
        decision=_decision(profile, like, matched),
    )
    write = f"https://t.me/{profile.username}" if matched and profile.username else None
    await deliver_photo(
        message,
        profile.photo_file_id,
        caption,
        feed_kb(profile.id, mode, index=index + 1, total=len(ids), write_url=write),
        edit=edit,
    )


async def _empty(message: Message, mode: str, *, edit: bool) -> None:
    if edit:
        try:
            await message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await message.answer(
        f"{EMPTY_BY_MODE.get(mode, t.FEED_EMPTY_ALL)}\n\n{t.FEED_FOOTER_EMPTY}",
        reply_markup=feed_filters_kb(),
    )


async def open_feed(message: Message, session: AsyncSession, config: Config) -> None:
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE, reply_markup=menu_for(message.from_user.id, config))
        return
    await touch_username(session, viewer, message.from_user.username)
    menu = menu_for(message.from_user.id, config)
    ids = await _ids(session, viewer, "all")
    if not ids:
        text = t.FEED_EMPTY_ALL
        if not viewer.is_active:
            text += f"\n\nТвоя анкета скрыта. Включить — {t.BTN_MY_PROFILE}."
        await message.answer(text, reply_markup=menu)
        return
    fresh = len(await _ids(session, viewer, "new"))
    await message.answer(
        t.feed_intro(len(ids), fresh, hidden=not viewer.is_active),
        reply_markup=menu,
    )
    await _show(message, session, viewer, ids[0], "all", edit=False)


def _parse(data: str) -> tuple[str, str, int] | None:
    parts = (data or "").split(":")
    if len(parts) != 4 or parts[0] != "f":
        return None
    action, code, raw = parts[1], parts[2], parts[3]
    if action not in {"n", "p", "y", "x", "f"} or code not in MODE_BY_CODE:
        return None
    if not raw.isdigit():
        return None
    return action, MODE_BY_CODE[code], int(raw)


async def _ack(callback: CallbackQuery, text: str = "", *, alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=alert)
    except Exception:
        pass


@router.callback_query(F.data == "f:noop")
async def feed_noop(callback: CallbackQuery) -> None:
    await _ack(callback)


@router.callback_query(F.data == "f:c")
async def feed_close(callback: CallbackQuery) -> None:
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await _ack(callback, t.TOAST_CLOSED)


@router.callback_query(F.data.startswith("f:"))
async def feed_action(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    parsed = _parse(callback.data or "")
    if parsed is None or callback.message is None:
        await _ack(callback, t.STALE_BUTTON, alert=True)
        return
    action, mode, profile_id = parsed
    viewer = await require_profile(session, callback.from_user.id)
    if not viewer:
        await _ack(callback, t.NO_PROFILE, alert=True)
        return

    if action == "f":
        ids = await _ids(session, viewer, mode)
        if not ids:
            await _empty(callback.message, mode, edit=True)
            await _ack(callback)
            return
        if profile_id == 0:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        target_id = profile_id if profile_id in ids else ids[0]
        await _show(
            callback.message,
            session,
            viewer,
            target_id,
            mode,
            edit=bool(callback.message.photo) and profile_id != 0,
        )
        await _ack(callback)
        return

    ids = await _ids(session, viewer, mode)
    if action in {"n", "p"}:
        if not ids:
            await _empty(callback.message, mode, edit=True)
            await _ack(callback)
            return
        if profile_id not in ids:
            await _show(callback.message, session, viewer, ids[0], mode, edit=True)
            await _ack(callback, t.TOAST_GONE)
            return
        pos = ids.index(profile_id)
        delta = 1 if action == "n" else -1
        new_pos = (pos + delta) % len(ids)
        wrapped = len(ids) > 1 and (
            (delta > 0 and pos == len(ids) - 1) or (delta < 0 and pos == 0)
        )
        await _show(callback.message, session, viewer, ids[new_pos], mode, edit=True)
        await _ack(callback, t.TOAST_WRAP if wrapped else "")
        return

    target = await ProfileRepo(session).get_by_id(profile_id)
    if not can_see(viewer, target) or target is None:
        ids = await _ids(session, viewer, mode)
        if ids:
            await _show(callback.message, session, viewer, ids[0], mode, edit=True)
        else:
            await _empty(callback.message, mode, edit=True)
        await _ack(callback, t.TOAST_GONE, alert=True)
        return

    before = await _ids(session, viewer, mode)
    pos = before.index(profile_id) if profile_id in before else 0
    outcome = await process_reaction(
        bot, session, viewer, target, is_like=(action == "y")
    )
    if outcome.status == "rejected":
        await _ack(callback, t.TOAST_GONE, alert=True)
        return

    after = await _ids(session, viewer, mode)
    if profile_id in after:
        await _show(callback.message, session, viewer, profile_id, mode, edit=True)
    elif after:
        await _show(
            callback.message,
            session,
            viewer,
            after[min(pos, len(after) - 1)],
            mode,
            edit=True,
        )
    else:
        await _empty(callback.message, mode, edit=True)

    if outcome.matched:
        toast, alert = t.TOAST_MATCH, True
    elif outcome.unmatched:
        toast, alert = t.TOAST_UNMATCH, True
    elif outcome.status == "exists":
        toast, alert = t.TOAST_SAME, False
    elif action == "y":
        toast, alert = t.TOAST_LIKE, False
    else:
        toast, alert = t.TOAST_NOPE, False
    await _ack(callback, toast, alert=alert)
