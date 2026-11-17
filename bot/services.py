from __future__ import annotations

import html
import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.models import Profile
from bot.db.repositories import AdminPrefRepo, LikeRepo, MatchRepo, ProfileRepo, ReactionOutcome
from bot.live_buttons import arm

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
            edited = await message.edit_media(
                media=InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup,
            )
            if reply_markup is not None and edited is not None:
                await arm(message.bot, edited.chat.id, edited.message_id)
            return edited
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                if reply_markup is not None:
                    await arm(message.bot, message.chat.id, message.message_id)
                return message
            logger.info("Не удалось обновить карточку, отправлю новую: %s", exc)
            try:
                await message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        except Exception:
            logger.exception("edit_media failed")
    try:
        sent = await message.answer_photo(
            photo=file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception:
        logger.warning("Фото не ушло, пробую текстом")
        try:
            sent = await message.answer(caption, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            logger.exception("Подпись с HTML не ушла")
            sent = await message.answer(caption, reply_markup=reply_markup)
    if reply_markup is not None and sent is not None:
        await arm(message.bot, sent.chat.id, sent.message_id)
    return sent


async def send_profile_card(
    message: Message,
    profile: Profile,
    *,
    prefix: str = "",
    reply_markup=None,
) -> Message | None:
    caption = (prefix + t.format_card(profile)).strip()
    return await deliver_photo(message, profile.photo_file_id, caption, reply_markup)


def admin_ids() -> frozenset[int]:
    try:
        from bot.config import load_config

        return load_config().admin_ids
    except Exception:
        return frozenset()


def _who(profile: Profile) -> str:
    if profile.username:
        return f"{profile.name} @{profile.username}"
    return profile.name


async def notify_admins(bot, session: AsyncSession, text: str, *, skip: set[int] | None = None) -> None:
    """Пишет только админам, которые сами включили /notify. Ошибка одному остальных не останавливает."""
    skip = skip or set()
    try:
        allowed = admin_ids()
        targets = await AdminPrefRepo(session).enabled_ids()
    except Exception:
        logger.exception("Не собрал список админов для уведомления")
        return
    for tg_id in targets:
        if tg_id not in allowed or tg_id in skip:
            continue
        try:
            await bot.send_message(tg_id, text)
        except Exception:
            logger.info("Админу не ушло уведомление tg=%s", tg_id)


async def notify_match(
    bot, session: AsyncSession, a: Profile, b: Profile, *, quiet_for: int | None = None
) -> None:
    match_repo = MatchRepo(session)
    _, created = await match_repo.create_if_needed(a.id, b.id)
    if not created:
        return

    for me, other in ((a, b), (b, a)):
        if quiet_for is not None and me.telegram_id == quiet_for:
            continue
        try:
            await bot.send_photo(
                chat_id=me.telegram_id,
                photo=other.photo_file_id,
                caption=match_text(other),
                parse_mode="HTML",
            )
        except Exception:
            logger.warning("Не удалось прислать пару tg=%s", me.telegram_id)
            try:
                await bot.send_message(
                    chat_id=me.telegram_id,
                    text=match_text(other),
                    parse_mode="HTML",
                )
            except Exception:
                logger.warning("Пара текстом тоже не ушла tg=%s", me.telegram_id)
    await notify_admins(
        bot,
        session,
        t.NOTIFY_PAIR.format(left=_who(a), right=_who(b)),
        skip={a.telegram_id, b.telegram_id},
    )


async def process_reaction(
    bot,
    session: AsyncSession,
    viewer: Profile,
    target: Profile,
    *,
    is_like: bool,
    quiet_for: int | None = None,
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
            await notify_match(bot, session, viewer, target, quiet_for=quiet_for)
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
