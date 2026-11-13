from __future__ import annotations

import html
import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.models import Profile
from bot.db.repositories import LikeRepo, MatchRepo, ProfileRepo, ReactionOutcome

logger = logging.getLogger(__name__)

GENDER_MAP = {
    t.GENDER_MALE: "male",
    t.GENDER_FEMALE: "female",
}
DANCE_MAP = {
    t.DANCE_NONE: "none",
    t.DANCE_SOME: "some",
    t.DANCE_CONFIDENT: "confident",
}

MODE_BY_CODE = {"a": "all", "u": "new", "l": "liked", "d": "nope"}
EMPTY_BY_MODE = {
    "all": t.FEED_EMPTY_ALL,
    "new": t.FEED_EMPTY_NEW,
    "liked": t.FEED_EMPTY_LIKED,
    "nope": t.FEED_EMPTY_NOPE,
}


def opposite_gender(gender: str) -> str:
    return "female" if gender == "male" else "male"


def can_see(viewer: Profile, target: Profile | None) -> bool:
    """То же правило, что у list_catalog: кого вообще можно открыть и лайкнуть."""
    if target is None or target.id == viewer.id:
        return False
    if not target.is_complete or target.is_banned or not target.is_active:
        return False
    if viewer.looking_for != "any" and target.gender != viewer.looking_for:
        return False
    if target.looking_for not in {viewer.gender, "any"}:
        return False
    return True


def contact_line(profile: Profile) -> str:
    if profile.username:
        return f"Написать: @{profile.username}"
    if profile.contact:
        return f"Контакт: {profile.contact}"
    return (
        f"Нет @username. Telegram id: {profile.telegram_id}. "
        "Можно попросить организаторов помочь связаться."
    )


def match_text(profile: Profile) -> str:
    return (
        f"<b>{html.escape(t.MATCH_INTRO)}</b>\n\n"
        f"{t.format_card(profile)}\n\n"
        f"{html.escape(contact_line(profile))}"
    )


def parse_height(raw: str) -> int | None:
    text = raw.strip().lower().replace("см", "").strip()
    if not text.isdigit():
        return None
    value = int(text)
    if 100 <= value <= 250:
        return value
    return None


async def require_profile(session: AsyncSession, telegram_id: int) -> Profile | None:
    profile = await ProfileRepo(session).get_by_tg(telegram_id)
    if not profile or not profile.is_complete:
        return None
    return profile


async def touch_username(session: AsyncSession, profile: Profile, username: str | None) -> None:
    await ProfileRepo(session).sync_username(profile, username)


async def deliver_photo(
    message: Message,
    file_id: str,
    caption: str,
    reply_markup=None,
    *,
    edit: bool = False,
) -> Message | None:
    if edit:
        try:
            return await message.edit_media(
                media=InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return message
            logger.info("Не удалось обновить карточку, отправлю новую: %s", exc)
            try:
                await message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        except Exception:
            logger.exception("edit_media failed")
    try:
        return await message.answer_photo(
            photo=file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception:
        logger.warning("Фото не ушло, пробую текстом")
        try:
            return await message.answer(caption, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            logger.exception("Подпись с HTML не ушла")
            return await message.answer(caption, reply_markup=reply_markup)


async def send_profile_card(
    message: Message,
    profile: Profile,
    *,
    prefix: str = "",
    reply_markup=None,
) -> Message | None:
    caption = (prefix + t.format_card(profile)).strip()
    return await deliver_photo(message, profile.photo_file_id, caption, reply_markup)


async def notify_match(bot, session: AsyncSession, a: Profile, b: Profile) -> None:
    from bot.keyboards.common import match_kb

    match_repo = MatchRepo(session)
    _, created = await match_repo.create_if_needed(a.id, b.id)
    if not created:
        return

    for me, other in ((a, b), (b, a)):
        try:
            await bot.send_photo(
                chat_id=me.telegram_id,
                photo=other.photo_file_id,
                caption=match_text(other),
                parse_mode="HTML",
                reply_markup=match_kb(other.username),
            )
        except Exception:
            logger.warning("Не удалось прислать пару tg=%s", me.telegram_id)
            try:
                await bot.send_message(
                    chat_id=me.telegram_id,
                    text=match_text(other),
                    parse_mode="HTML",
                    reply_markup=match_kb(other.username),
                )
            except Exception:
                logger.warning("Пара текстом тоже не ушла tg=%s", me.telegram_id)


async def process_reaction(
    bot,
    session: AsyncSession,
    viewer: Profile,
    target: Profile,
    *,
    is_like: bool,
) -> ReactionOutcome:
    if not can_see(viewer, target):
        return ReactionOutcome(status="rejected")

    like_repo = LikeRepo(session)
    had_match = await MatchRepo(session).get(viewer.id, target.id) is not None
    result = await like_repo.add(viewer.id, target.id, is_like=is_like)
    if result.status == "rejected":
        return ReactionOutcome(status="rejected")
    if result.status == "exists":
        return ReactionOutcome(status="exists", matched=had_match and is_like)

    if is_like:
        mutual = await like_repo.has_mutual_like(viewer.id, target.id)
        if mutual:
            await notify_match(bot, session, viewer, target)
            return ReactionOutcome(status=result.status, matched=True)
        if result.status == "created":
            try:
                await bot.send_message(target.telegram_id, t.SOMEONE_LIKED_YOU)
            except Exception:
                logger.info("Не предупредили о лайке tg=%s", target.telegram_id)
        return ReactionOutcome(status=result.status)

    if had_match:
        await MatchRepo(session).delete_pair(viewer.id, target.id)
        try:
            await bot.send_message(
                target.telegram_id,
                t.unmatched_notice(viewer.name),
                parse_mode="HTML",
            )
        except Exception:
            logger.info("Не предупредили о снятой паре tg=%s", target.telegram_id)
        return ReactionOutcome(status=result.status, unmatched=True)
    return ReactionOutcome(status=result.status)
