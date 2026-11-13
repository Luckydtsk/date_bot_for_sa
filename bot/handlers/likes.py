"""Кто лайкнул тебя и ещё ждёт ответ."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.models import Profile
from bot.db.repositories import ProfileRepo
from bot.keyboards.common import likes_kb, menu_for
from bot.services import can_see, deliver_photo, process_reaction, require_profile

router = Router(name="likes")


async def _incoming(session: AsyncSession, viewer: Profile) -> list[Profile]:
    rows = await ProfileRepo(session).incoming_likes(viewer)
    return [profile for profile, _like in rows]


async def open_likes(message: Message, session: AsyncSession, config: Config) -> None:
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE, reply_markup=menu_for(message.from_user.id, config))
        return
    people = await _incoming(session, viewer)
    if not people:
        await message.answer(t.LIKES_EMPTY, reply_markup=menu_for(message.from_user.id, config))
        return
    await message.answer(
        t.likes_intro(len(people)),
        reply_markup=menu_for(message.from_user.id, config),
    )
    await _send(message, people[0], index=1, total=len(people))


async def _send(message: Message, profile: Profile, *, index: int, total: int) -> None:
    await deliver_photo(
        message,
        profile.photo_file_id,
        t.likes_caption(profile, index=index, total=total),
        likes_kb(profile.id),
    )


async def _ack(callback: CallbackQuery, text: str = "", *, alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=alert)
    except Exception:
        pass


@router.callback_query(F.data == "in:c")
async def likes_close(callback: CallbackQuery) -> None:
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await _ack(callback, t.TOAST_CLOSED)


@router.callback_query(F.data.startswith("in:"))
async def likes_answer(
    callback: CallbackQuery, session: AsyncSession, bot: Bot, config: Config
) -> None:
    if callback.message is None:
        await _ack(callback)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or parts[1] not in {"y", "x"} or not parts[2].isdigit():
        await _ack(callback, t.STALE_BUTTON, alert=True)
        return
    viewer = await require_profile(session, callback.from_user.id)
    if not viewer:
        await _ack(callback, t.NO_PROFILE, alert=True)
        return
    target = await ProfileRepo(session).get_by_id(int(parts[2]))
    if not can_see(viewer, target) or target is None:
        await _ack(callback, t.TOAST_GONE, alert=True)
        return
    if not await ProfileRepo(session).has_pending_incoming_like(viewer.id, target.id):
        await _ack(callback, t.TOAST_SAME)
        return

    outcome = await process_reaction(
        bot, session, viewer, target, is_like=(parts[1] == "y")
    )
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if outcome.matched:
        toast, alert = t.TOAST_MATCH, True
    elif outcome.status == "rejected":
        toast, alert = t.TOAST_GONE, True
    elif parts[1] == "y":
        toast, alert = t.TOAST_LIKE, False
    else:
        toast, alert = t.TOAST_NOPE, False

    people = await _incoming(session, viewer)
    if people:
        await _send(callback.message, people[0], index=1, total=len(people))
    else:
        await callback.message.answer(
            t.LIKES_EMPTY, reply_markup=menu_for(callback.from_user.id, config)
        )
    await _ack(callback, toast, alert=alert)
