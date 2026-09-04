from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.models import Profile
from bot.db.repositories import LikeRepo, MatchRepo, ProfileRepo
from bot.keyboards.cleanup import remember_chat_keyboard
from bot.keyboards.common import match_kb

GENDER_MAP = {
    t.GENDER_MALE: "male",
    t.GENDER_FEMALE: "female",
}
DANCE_MAP = {
    t.DANCE_NONE: "none",
    t.DANCE_SOME: "some",
    t.DANCE_CONFIDENT: "confident",
}

TELEGRAM_CAPTION_LIMIT = 1024


def opposite_gender(gender: str) -> str:
    return "female" if gender == "male" else "male"


def contact_line(profile: Profile) -> str:
    if profile.username:
        return t.MATCH_CONTACT_USERNAME.format(username=profile.username)
    if profile.contact:
        return t.MATCH_CONTACT_MANUAL.format(contact=profile.contact)
    return t.MATCH_CONTACT_ID.format(tg_id=profile.telegram_id)


def _clip_caption(text: str) -> str:
    if len(text) <= TELEGRAM_CAPTION_LIMIT:
        return text
    return text[: TELEGRAM_CAPTION_LIMIT - 1] + "…"


def is_reactable_target(viewer: Profile, target: Profile | None) -> bool:
    if target is None:
        return False
    if target.id == viewer.id:
        return False
    if not target.is_complete or target.is_banned:
        return False
    return True


async def send_profile_card(
    target: Message | Bot,
    profile: Profile,
    *,
    chat_id: int | None = None,
    reply_markup=None,
    prefix: str = "",
) -> Message | None:
    caption = _clip_caption((prefix + t.format_card(profile)).strip())
    try:
        if isinstance(target, Message):
            return await target.answer_photo(
                photo=profile.photo_file_id,
                caption=caption,
                reply_markup=reply_markup,
            )
        assert chat_id is not None
        return await target.send_photo(
            chat_id=chat_id,
            photo=profile.photo_file_id,
            caption=caption,
            reply_markup=reply_markup,
        )
    except Exception:
        # Фото могло устареть — хотя бы текст
        try:
            if isinstance(target, Message):
                return await target.answer(caption, reply_markup=reply_markup)
            assert chat_id is not None
            return await target.send_message(
                chat_id=chat_id, text=caption, reply_markup=reply_markup
            )
        except Exception:
            return None


async def notify_match(
    bot: Bot,
    session: AsyncSession,
    a: Profile,
    b: Profile,
) -> None:
    """Уведомляет обоих о матче (идемпотентно на уровне MatchRepo)."""
    match_repo = MatchRepo(session)
    _, created = await match_repo.create_if_needed(a.id, b.id)
    if not created:
        return

    for me, other in ((a, b), (b, a)):
        text = _clip_caption(
            f"{t.MATCH_TITLE}\n\n{t.format_card(other)}\n\n{contact_line(other)}"
        )
        sent = None
        try:
            sent = await bot.send_photo(
                chat_id=me.telegram_id,
                photo=other.photo_file_id,
                caption=text,
                reply_markup=match_kb(other.username),
            )
        except Exception:
            try:
                sent = await bot.send_message(
                    chat_id=me.telegram_id,
                    text=text,
                    reply_markup=match_kb(other.username),
                )
            except Exception:
                pass
        if sent is not None:
            remember_chat_keyboard(me.telegram_id, sent.message_id)


async def process_reaction(
    bot: Bot,
    session: AsyncSession,
    viewer: Profile,
    target: Profile,
    *,
    is_like: bool,
) -> bool:
    """
    Сохраняет реакцию. Возвращает True, если случился новый матч.
    Повторные клики и невалидные цели игнорируются.
    """
    if not is_reactable_target(viewer, target):
        return False

    like_repo = LikeRepo(session)
    result = await like_repo.add(viewer.id, target.id, is_like=is_like)
    if result.status != "created":
        return False

    if not is_like:
        return False

    mutual = await like_repo.has_mutual_like(viewer.id, target.id)
    if mutual:
        await notify_match(bot, session, viewer, target)
        return True

    try:
        await bot.send_message(target.telegram_id, t.SOMEONE_LIKED_YOU)
    except Exception:
        pass
    return False


async def require_profile(session: AsyncSession, telegram_id: int) -> Profile | None:
    profile = await ProfileRepo(session).get_by_tg(telegram_id)
    if not profile or not profile.is_complete:
        return None
    return profile
