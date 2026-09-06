from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio

from bot import texts as t
from bot.config import Config
from bot.db.models import Profile
from bot.db.repositories import ProfileRepo, StatsRepo
from bot.keyboards.cleanup import clear_tracked_keyboards, track_keyboard_message
from bot.keyboards.common import admin_back_kb, admin_menu_kb, admin_pick_kb, menu_for
from bot.services import send_profile_card
from bot.states.profile import AdminBroadcast, AdminPickUser

router = Router(name="admin")

_PAGE_SIZE = 10
_PICK_ACTIONS = frozenset({"view", "ban", "unban"})


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


def _button_label(profile: Profile) -> str:
    flag = "🚫 " if profile.is_banned else ""
    text = f"{flag}{profile.name} · {profile.telegram_id}"
    return text[:64]


def _users_kb(
    profiles: list[Profile],
    *,
    offset: int,
    total: int,
    action: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_button_label(p),
                callback_data=f"admin:pick:{action}:{p.telegram_id}",
            )
        ]
        for p in profiles
    ]
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"admin:list:{action}:{max(0, offset - _PAGE_SIZE)}",
            )
        )
    if offset + _PAGE_SIZE < total:
        nav.append(
            InlineKeyboardButton(
                text="Далее →",
                callback_data=f"admin:list:{action}:{offset + _PAGE_SIZE}",
            )
        )
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _resolve_profile(session: AsyncSession, raw: str) -> Profile | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    repo = ProfileRepo(session)
    if raw.isdigit():
        return await repo.get_by_tg(int(raw))
    return await repo.get_by_username(raw)


async def open_admin_panel(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(t.ADMIN_PANEL_TITLE, reply_markup=admin_menu_kb())


async def _show_stats(message: Message, session: AsyncSession) -> None:
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


async def _send_users_page(
    message: Message,
    session: AsyncSession,
    *,
    offset: int,
    action: str = "view",
    config: Config | None = None,
) -> None:
    repo = ProfileRepo(session)
    admin_ids = config.admin_ids if config else frozenset()

    if action == "unban":
        total = await repo.count_banned()
        if total == 0:
            await message.answer(t.USERS_BANNED_EMPTY)
            return
        profiles = await repo.list_banned(offset=offset, limit=_PAGE_SIZE)
        empty_text = t.USERS_BANNED_EMPTY
    elif action == "ban":
        total = await repo.count_bannable(exclude_tg_ids=admin_ids)
        if total == 0:
            await message.answer(t.USERS_BAN_EMPTY)
            return
        profiles = await repo.list_bannable(
            exclude_tg_ids=admin_ids, offset=offset, limit=_PAGE_SIZE
        )
        empty_text = t.USERS_BAN_EMPTY
    else:
        total = await repo.count_complete()
        if total == 0:
            await message.answer(t.USERS_EMPTY)
            return
        profiles = await repo.list_all(offset=offset, limit=_PAGE_SIZE)
        empty_text = t.USERS_EMPTY

    if not profiles:
        await message.answer(empty_text)
        return
    start = offset + 1
    end = offset + len(profiles)
    lines = [
        t.USERS_PAGE.format(start=start, end=end, total=total),
        t.USERS_PICK_HINT,
        "",
    ]
    for i, profile in enumerate(profiles, start=start):
        lines.append(_format_user_line(i, profile))
    await message.answer(
        "\n".join(lines),
        reply_markup=_users_kb(profiles, offset=offset, total=total, action=action),
    )


async def _show_user_card(
    message: Message, profile: Profile, state: FSMContext
) -> None:
    uname = f"@{profile.username}" if profile.username else "нет username"
    prefix = (
        f"Админ-просмотр\n"
        f"tg id: {profile.telegram_id} · {uname}{_flags(profile)}\n\n"
    )
    sent = await send_profile_card(message, profile, prefix=prefix)
    await track_keyboard_message(state, sent)


async def _apply_ban(
    message: Message,
    session: AsyncSession,
    profile: Profile,
    config: Config,
    *,
    banned: bool,
) -> None:
    if banned and profile.telegram_id in config.admin_ids:
        await message.answer(t.BAN_ADMIN_FORBIDDEN)
        return
    await ProfileRepo(session).set_banned(profile.telegram_id, banned)
    tmpl = t.BAN_DONE if banned else t.UNBAN_DONE
    await message.answer(tmpl.format(tg_id=profile.telegram_id))


async def _start_pick(
    message: Message, state: FSMContext, *, action: str, prompt: str
) -> None:
    await state.set_state(AdminPickUser.waiting)
    await state.update_data(admin_action=action)
    await message.answer(prompt, reply_markup=admin_pick_kb())


async def _broadcast_now(
    bot: Bot, session: AsyncSession, text: str, message: Message
) -> None:
    ids = await ProfileRepo(session).all_telegram_ids(
        only_complete=True, only_active=True
    )
    await _send_broadcast(bot, ids, text, message)


async def _send_broadcast(bot: Bot, ids: list[int], text: str, message: Message) -> None:
    """Шлём без дальнейших запросов к БД: ids уже загружены."""
    ok = fail = 0
    for i, tg_id in enumerate(ids):
        try:
            await bot.send_message(tg_id, text)
            ok += 1
        except Exception:
            fail += 1
        if i + 1 < len(ids):
            await asyncio.sleep(0.05)
    await message.answer(t.BROADCAST_DONE.format(ok=ok, fail=fail, total=len(ids)))


# --- Panel entry ---


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN)
async def btn_admin(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    await open_admin_panel(message, state, bot, config)


@router.message(Command("admin"))
async def cmd_admin_help(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await open_admin_panel(message, state, bot, config)
    await message.answer(t.ADMIN_HELP)


@router.message(F.text.in_({t.BTN_ADMIN_BACK, "« В меню"}))
async def btn_admin_back(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(
        t.MENU_TITLE, reply_markup=menu_for(message.from_user.id, config)
    )


# --- Admin submenu buttons ---


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN_STATS)
async def btn_admin_stats(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await state.clear()
    await _show_stats(message, session)


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN_USERS)
async def btn_admin_users(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await state.clear()
    await _send_users_page(message, session, offset=0, action="view", config=config)


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN_USER)
async def btn_admin_user(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await _start_pick(message, state, action="view", prompt=t.ADMIN_PICK_VIEW)


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN_BAN)
async def btn_admin_ban(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await _start_pick(message, state, action="ban", prompt=t.ADMIN_PICK_BAN)


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN_UNBAN)
async def btn_admin_unban(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await _start_pick(message, state, action="unban", prompt=t.ADMIN_PICK_UNBAN)


@router.message(StateFilter(default_state), F.text == t.BTN_ADMIN_BROADCAST)
async def btn_admin_broadcast(
    message: Message, state: FSMContext, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await state.set_state(AdminBroadcast.waiting_text)
    await message.answer(t.ADMIN_BROADCAST_ASK, reply_markup=admin_back_kb())


@router.message(AdminPickUser.waiting, F.text == t.BTN_ADMIN_PICK_LIST)
async def pick_open_list(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    data = await state.get_data()
    action = data.get("admin_action", "view")
    if action not in _PICK_ACTIONS:
        action = "view"
    await _send_users_page(
        message, session, offset=0, action=action, config=config
    )


@router.message(AdminPickUser.waiting, F.text == t.CANCEL)
async def pick_cancel(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await state.clear()
    await message.answer(t.ADMIN_PANEL_TITLE, reply_markup=admin_menu_kb())


@router.message(AdminPickUser.waiting, F.text)
async def pick_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    config: Config,
) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    data = await state.get_data()
    action = data.get("admin_action", "view")
    profile = await _resolve_profile(session, message.text or "")
    if not profile or not profile.is_complete:
        await message.answer(t.USER_NOT_FOUND, reply_markup=admin_pick_kb())
        return
    await state.clear()
    await message.answer(t.ADMIN_PANEL_TITLE, reply_markup=admin_menu_kb())
    if action == "ban":
        await _apply_ban(message, session, profile, config, banned=True)
    elif action == "unban":
        await _apply_ban(message, session, profile, config, banned=False)
    else:
        await _show_user_card(message, profile, state)


@router.callback_query(F.data.startswith("admin:list:"))
async def users_page(
    callback: CallbackQuery, session: AsyncSession, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    if not callback.message:
        await callback.answer()
        return
    parts = callback.data.split(":")
    # admin:list:{action}:{offset}
    if len(parts) != 4:
        await callback.answer()
        return
    action, offset_s = parts[2], parts[3]
    if action not in _PICK_ACTIONS or not offset_s.isdigit():
        await callback.answer()
        return
    await callback.message.delete()
    await _send_users_page(
        callback.message,
        session,
        offset=int(offset_s),
        action=action,
        config=config,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:"))
async def users_page_legacy(
    callback: CallbackQuery, session: AsyncSession, config: Config
) -> None:
    """Старые кнопки пагинации /users."""
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    if not callback.message:
        await callback.answer()
        return
    offset_s = callback.data.split(":")[-1]
    if not offset_s.isdigit():
        await callback.answer()
        return
    await callback.message.delete()
    await _send_users_page(
        callback.message,
        session,
        offset=int(offset_s),
        action="view",
        config=config,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:pick:"))
async def pick_from_list(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    config: Config,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    if not callback.message:
        await callback.answer()
        return
    parts = callback.data.split(":")
    # admin:pick:{action}:{tg_id}
    if len(parts) != 4:
        await callback.answer()
        return
    action, tg_s = parts[2], parts[3]
    if action not in _PICK_ACTIONS or not tg_s.isdigit():
        await callback.answer()
        return
    profile = await ProfileRepo(session).get_by_tg(int(tg_s))
    if not profile or not profile.is_complete:
        await callback.answer(t.USER_NOT_FOUND, show_alert=True)
        return
    await state.clear()
    await callback.message.answer(t.ADMIN_PANEL_TITLE, reply_markup=admin_menu_kb())
    if action == "ban":
        await _apply_ban(callback.message, session, profile, config, banned=True)
    elif action == "unban":
        await _apply_ban(callback.message, session, profile, config, banned=False)
    else:
        await _show_user_card(callback.message, profile, state)
    await callback.answer()


# --- Slash commands (совместимость) ---


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await _show_stats(message, session)


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await _send_users_page(message, session, offset=0, action="view", config=config)


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
    if not raw:
        await _start_pick(message, state, action="view", prompt=t.ADMIN_PICK_VIEW)
        return
    profile = await _resolve_profile(session, raw)
    if not profile or not profile.is_complete:
        await message.answer(t.USER_NOT_FOUND)
        return
    await _show_user_card(message, profile, state)


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
        await state.set_state(AdminBroadcast.waiting_text)
        await message.answer(t.ADMIN_BROADCAST_ASK, reply_markup=admin_back_kb())
        return
    await _broadcast_now(bot, session, text, message)


@router.message(AdminBroadcast.waiting_text, F.text == t.CANCEL)
async def broadcast_cancel(
    message: Message, state: FSMContext, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await state.clear()
    await message.answer(t.ADMIN_PANEL_TITLE, reply_markup=admin_menu_kb())


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
    # Старая клавиатура могла ещё показывать лишние кнопки
    if message.text in {
        t.BTN_ADMIN_PICK_LIST,
        t.BTN_ADMIN_BACK,
        t.BTN_ADMIN_STATS,
        t.BTN_ADMIN_USERS,
        t.BTN_ADMIN_USER,
        t.BTN_ADMIN_BROADCAST,
        t.BTN_ADMIN_BAN,
        t.BTN_ADMIN_UNBAN,
        t.BTN_ADMIN,
    }:
        await message.answer(t.ADMIN_BROADCAST_ASK, reply_markup=admin_back_kb())
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(t.BROADCAST_USAGE, reply_markup=admin_back_kb())
        return
    await state.clear()
    await message.answer(t.ADMIN_PANEL_TITLE, reply_markup=admin_menu_kb())
    await _broadcast_now(bot, session, text, message)


@router.message(Command("ban"))
async def cmd_ban(
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
    if not raw:
        await _start_pick(message, state, action="ban", prompt=t.ADMIN_PICK_BAN)
        return
    profile = await _resolve_profile(session, raw)
    if not profile or not profile.is_complete:
        await message.answer(t.USER_NOT_FOUND)
        return
    await _apply_ban(message, session, profile, config, banned=True)


@router.message(Command("unban"))
async def cmd_unban(
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
    if not raw:
        await _start_pick(message, state, action="unban", prompt=t.ADMIN_PICK_UNBAN)
        return
    profile = await _resolve_profile(session, raw)
    if not profile:
        await message.answer(t.USER_NOT_FOUND)
        return
    await _apply_ban(message, session, profile, config, banned=False)
