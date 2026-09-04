from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.models import Profile
from bot.db.repositories import ProfileRepo, StatsRepo
from bot.keyboards.cleanup import track_keyboard_message
from bot.services import send_profile_card
from bot.states.profile import AdminBroadcast

router = Router(name="admin")

_PAGE_SIZE = 10


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _gender_label(gender: str) -> str:
    return "парень" if gender == "male" else "девушка"


def _flags(profile: Profile) -> str:
    bits = []
    if not profile.is_active:
        bits.append("пауза")
    if profile.is_banned:
        bits.append("бан")
    return f" · {', '.join(bits)}" if bits else ""


def _format_user_line(n: int, profile: Profile) -> str:
    username = f" · @{profile.username}" if profile.username else ""
    return t.USER_LINE.format(
        n=n,
        name=profile.name,
        gender=_gender_label(profile.gender),
        faculty=profile.faculty,
        tg_id=profile.telegram_id,
        username=username,
        flags=_flags(profile),
    )


def _users_kb(offset: int, total: int) -> InlineKeyboardMarkup | None:
    buttons: list[InlineKeyboardButton] = []
    if offset > 0:
        buttons.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"admin:users:{max(0, offset - _PAGE_SIZE)}",
            )
        )
    if offset + _PAGE_SIZE < total:
        buttons.append(
            InlineKeyboardButton(
                text="Далее →",
                callback_data=f"admin:users:{offset + _PAGE_SIZE}",
            )
        )
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


@router.message(Command("admin"))
async def cmd_admin_help(message: Message, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await message.answer(
        "Админка:\n"
        "/stats — цифры\n"
        "/users — все анкеты\n"
        "/user <telegram_id> — одна анкета с фото\n"
        "/broadcast текст — рассылка\n"
        "/ban <telegram_id>\n"
        "/unban <telegram_id>"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    stats = await StatsRepo(session).collect()
    await message.answer(
        t.STATS_TEMPLATE.format(
            profiles=stats.profiles,
            active=stats.active,
            paused=stats.paused,
            likes=stats.likes,
            matches=stats.matches,
            banned=stats.banned,
        )
    )


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await _send_users_page(message, session, offset=0)


@router.callback_query(F.data.startswith("admin:users:"))
async def users_page(
    callback: CallbackQuery, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    if not callback.message:
        await callback.answer()
        return
    offset = int(callback.data.split(":")[-1])
    await callback.message.delete()
    await _send_users_page(callback.message, session, offset=offset)
    await callback.answer()


async def _send_users_page(
    message: Message, session: AsyncSession, *, offset: int
) -> None:
    repo = ProfileRepo(session)
    total = await repo.count_complete()
    if total == 0:
        await message.answer(t.USERS_EMPTY)
        return
    profiles = await repo.list_all(offset=offset, limit=_PAGE_SIZE)
    if not profiles:
        await message.answer(t.USERS_EMPTY)
        return
    start = offset + 1
    end = offset + len(profiles)
    lines = [
        t.USERS_PAGE.format(start=start, end=end, total=total),
        "",
    ]
    for i, profile in enumerate(profiles, start=start):
        lines.append(_format_user_line(i, profile))
    lines.append("")
    lines.append("Карточка: /user <telegram_id>")
    await message.answer(
        "\n".join(lines),
        reply_markup=_users_kb(offset, total),
    )


@router.message(Command("user"))
async def cmd_user(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    config: Config,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    raw = (command.args or "").strip()
    if not raw.isdigit():
        await message.answer(t.USERS_USAGE)
        return
    profile = await ProfileRepo(session).get_by_tg(int(raw))
    if not profile or not profile.is_complete:
        await message.answer(t.USER_NOT_FOUND)
        return
    uname = f"@{profile.username}" if profile.username else "нет username"
    prefix = (
        f"Админ-просмотр\n"
        f"tg id: {profile.telegram_id} · {uname}{_flags(profile)}\n\n"
    )
    sent = await send_profile_card(message, profile, prefix=prefix)
    await track_keyboard_message(state, sent)


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    text = (command.args or "").strip()
    if not text:
        await message.answer(
            t.BROADCAST_USAGE + "\nИли пришли текст следующим сообщением."
        )
        await state.set_state(AdminBroadcast.waiting_text)
        return
    await _send_broadcast(bot, session, text, message)


@router.message(AdminBroadcast.waiting_text, F.text)
async def broadcast_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(t.BROADCAST_USAGE)
        return
    await state.clear()
    await _send_broadcast(bot, session, text, message)


async def _send_broadcast(
    bot: Bot, session: AsyncSession, text: str, message: Message
) -> None:
    ids = await ProfileRepo(session).all_telegram_ids(only_active=True)
    ok = fail = 0
    for tg_id in ids:
        try:
            await bot.send_message(tg_id, text)
            ok += 1
        except Exception:
            fail += 1
    await message.answer(t.BROADCAST_DONE.format(ok=ok, fail=fail, total=len(ids)))


@router.message(Command("ban"))
async def cmd_ban(
    message: Message, command: CommandObject, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    raw = (command.args or "").strip()
    if not raw.isdigit():
        await message.answer(t.BAN_USAGE)
        return
    tg_id = int(raw)
    profile = await ProfileRepo(session).set_banned(tg_id, True)
    if not profile:
        await message.answer(t.USER_NOT_FOUND)
        return
    await message.answer(t.BAN_DONE.format(tg_id=tg_id))


@router.message(Command("unban"))
async def cmd_unban(
    message: Message, command: CommandObject, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    raw = (command.args or "").strip()
    if not raw.isdigit():
        await message.answer(t.UNBAN_USAGE)
        return
    tg_id = int(raw)
    profile = await ProfileRepo(session).set_banned(tg_id, False)
    if not profile:
        await message.answer(t.USER_NOT_FOUND)
        return
    await message.answer(t.UNBAN_DONE.format(tg_id=tg_id))
