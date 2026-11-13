"""Админка организатора. Кнопки под сообщением, меню участника остаётся внизу."""

import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.models import Profile
from bot.db.repositories import ProfileRepo, StatsRepo
from bot.keyboards.common import admin_panel_kb, admin_pick_kb, is_admin
from bot.live_buttons import answer_inline
from bot.services import deliver_photo
from bot.states.profile import AdminBroadcast, AdminPickUser

router = Router(name="admin")

_PAGE = 10
_ACTIONS = frozenset({"view", "ban", "unban"})


def _gender(gender: str) -> str:
    return "парень" if gender == "male" else "девушка"


def _flags(profile: Profile) -> str:
    bits = []
    if not profile.is_active:
        bits.append("скрыта")
    if profile.is_banned:
        bits.append("бан")
    return f" · {', '.join(bits)}" if bits else ""


def _line(n: int, profile: Profile) -> str:
    username = f" · @{profile.username}" if profile.username else ""
    return t.USER_LINE.format(
        n=n,
        name=profile.name,
        gender=_gender(profile.gender),
        faculty=profile.faculty,
        tg_id=profile.telegram_id,
        username=username,
        flags=_flags(profile),
    )


def _users_kb(profiles: list[Profile], *, offset: int, total: int, action: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=(("🚫 " if profile.is_banned else "") + f"{profile.name} · {profile.telegram_id}")[:64],
                callback_data=f"admin:pick:{action}:{profile.telegram_id}",
            )
        ]
        for profile in profiles
    ]
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"admin:list:{action}:{max(0, offset - _PAGE)}",
            )
        )
    if offset + _PAGE < total:
        nav.append(
            InlineKeyboardButton(
                text="Далее →",
                callback_data=f"admin:list:{action}:{offset + _PAGE}",
            )
        )
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="admin:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def open_admin_panel(message: Message, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await answer_inline(message, t.ADMIN_PANEL_TITLE, admin_panel_kb(), parse_mode="HTML")


async def _resolve(session: AsyncSession, raw: str) -> Profile | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    repo = ProfileRepo(session)
    if raw.isdigit():
        return await repo.get_by_tg(int(raw))
    return await repo.get_by_username(raw)


async def _stats(message: Message, session: AsyncSession) -> None:
    stats = await StatsRepo(session).collect()
    await message.answer(
        t.STATS_TEMPLATE.format(
            profiles=stats.profiles,
            active=stats.active,
            paused=stats.paused,
            likes=stats.likes,
            matches=stats.matches,
            banned=stats.banned,
        ),
        parse_mode="HTML",
    )


async def _page(
    message: Message,
    session: AsyncSession,
    *,
    offset: int,
    action: str,
    config: Config,
) -> None:
    repo = ProfileRepo(session)
    if action == "unban":
        total = await repo.count_banned()
        profiles = await repo.list_banned(offset=offset, limit=_PAGE) if total else []
        empty = t.USERS_BANNED_EMPTY
    elif action == "ban":
        total = await repo.count_bannable(exclude_tg_ids=config.admin_ids)
        profiles = (
            await repo.list_bannable(exclude_tg_ids=config.admin_ids, offset=offset, limit=_PAGE)
            if total
            else []
        )
        empty = t.USERS_BAN_EMPTY
    else:
        total = await repo.count_complete()
        profiles = await repo.list_all(offset=offset, limit=_PAGE) if total else []
        empty = t.USERS_EMPTY
    if not profiles:
        await answer_inline(message, empty, admin_panel_kb())
        return
    start = offset + 1
    lines = [t.USERS_PAGE.format(start=start, end=offset + len(profiles), total=total), ""]
    for index, profile in enumerate(profiles, start=start):
        lines.append(_line(index, profile))
    await answer_inline(
        message,
        "\n".join(lines),
        _users_kb(profiles, offset=offset, total=total, action=action),
    )


async def _card(message: Message, profile: Profile) -> None:
    uname = f"@{profile.username}" if profile.username else "нет username"
    prefix = (
        f"<b>Анкета участника</b>\n"
        f"id {profile.telegram_id} · {uname}{_flags(profile)}\n\n"
    )
    await deliver_photo(message, profile.photo_file_id, prefix + t.format_card(profile))


async def _ban(
    message: Message, session: AsyncSession, profile: Profile, config: Config, *, banned: bool
) -> None:
    if banned and profile.telegram_id in config.admin_ids:
        await message.answer(t.BAN_ADMIN_FORBIDDEN)
        return
    await ProfileRepo(session).set_banned(profile.telegram_id, banned)
    template = t.BAN_DONE if banned else t.UNBAN_DONE
    await message.answer(template.format(tg_id=profile.telegram_id))


async def _ask(message: Message, state: FSMContext, *, action: str, prompt: str) -> None:
    await state.set_state(AdminPickUser.waiting)
    await state.update_data(admin_action=action)
    await answer_inline(message, prompt, admin_pick_kb())


async def _broadcast(bot: Bot, session: AsyncSession, text: str, message: Message) -> None:
    ids = await ProfileRepo(session).all_telegram_ids(only_complete=True, only_active=True)
    ok = fail = 0
    for index, tg_id in enumerate(ids):
        try:
            await bot.send_message(tg_id, text)
            ok += 1
        except Exception:
            fail += 1
        if index + 1 < len(ids):
            await asyncio.sleep(0.05)
    await message.answer(t.BROADCAST_DONE.format(ok=ok, fail=fail, total=len(ids)))


async def _apply_action(
    message: Message,
    session: AsyncSession,
    config: Config,
    profile: Profile,
    action: str,
) -> None:
    if action == "ban":
        await _ban(message, session, profile, config, banned=True)
    elif action == "unban":
        await _ban(message, session, profile, config, banned=False)
    else:
        await _card(message, profile)


def _guard(user_id: int, config: Config) -> bool:
    return is_admin(user_id, config)


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    if callback.message and _guard(callback.from_user.id, config):
        await answer_inline(
            callback.message, t.ADMIN_PANEL_TITLE, admin_panel_kb(), parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_stats(callback: CallbackQuery, session: AsyncSession, config: Config) -> None:
    if not _guard(callback.from_user.id, config) or callback.message is None:
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    await _stats(callback.message, session)
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def cb_users(callback: CallbackQuery, session: AsyncSession, config: Config) -> None:
    if not _guard(callback.from_user.id, config) or callback.message is None:
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    await _page(callback.message, session, offset=0, action="view", config=config)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ask:"))
async def cb_ask(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _guard(callback.from_user.id, config) or callback.message is None:
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    action = (callback.data or "").rsplit(":", 1)[-1]
    prompts = {
        "view": t.ADMIN_PICK_VIEW,
        "ban": t.ADMIN_PICK_BAN,
        "unban": t.ADMIN_PICK_UNBAN,
        "broadcast": t.ADMIN_BROADCAST_ASK,
    }
    if action == "broadcast":
        await state.set_state(AdminBroadcast.waiting_text)
        await answer_inline(callback.message, prompts["broadcast"], admin_pick_kb())
        await callback.answer()
        return
    if action not in _ACTIONS:
        await callback.answer()
        return
    await _ask(callback.message, state, action=action, prompt=prompts[action])
    await callback.answer()


@router.callback_query(F.data == "admin:openlist")
async def cb_open_list(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _guard(callback.from_user.id, config) or callback.message is None:
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    data = await state.get_data()
    action = data.get("admin_action", "view")
    if action not in _ACTIONS:
        action = "view"
    await _page(callback.message, session, offset=0, action=action, config=config)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:list:"))
async def cb_list(callback: CallbackQuery, session: AsyncSession, config: Config) -> None:
    if not _guard(callback.from_user.id, config) or callback.message is None:
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or parts[2] not in _ACTIONS or not parts[3].isdigit():
        await callback.answer()
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _page(
        callback.message,
        session,
        offset=int(parts[3]),
        action=parts[2],
        config=config,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:pick:"))
async def cb_pick(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _guard(callback.from_user.id, config) or callback.message is None:
        await callback.answer(t.ADMIN_ONLY, show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 4 or parts[2] not in _ACTIONS or not parts[3].isdigit():
        await callback.answer()
        return
    profile = await ProfileRepo(session).get_by_tg(int(parts[3]))
    if not profile or not profile.is_complete:
        await callback.answer(t.USER_NOT_FOUND, show_alert=True)
        return
    await state.clear()
    await _apply_action(callback.message, session, config, profile, parts[2])
    await callback.answer()


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext, session: AsyncSession, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    await _stats(message, session)


@router.message(F.text == t.BTN_ADMIN_STATS)
async def btn_stats(message: Message, state: FSMContext, session: AsyncSession, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        return
    await state.clear()
    await _stats(message, session)


@router.message(Command("users"))
async def cmd_users(message: Message, state: FSMContext, session: AsyncSession, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    await _page(message, session, offset=0, action="view", config=config)


@router.message(F.text == t.BTN_ADMIN_USERS)
async def btn_users(message: Message, state: FSMContext, session: AsyncSession, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        return
    await state.clear()
    await _page(message, session, offset=0, action="view", config=config)


@router.message(Command("user"))
async def cmd_user(
    message: Message, command: CommandObject, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _guard(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    raw = (command.args or "").strip()
    if not raw:
        await _ask(message, state, action="view", prompt=t.ADMIN_PICK_VIEW)
        return
    profile = await _resolve(session, raw)
    if not profile or not profile.is_complete:
        await message.answer(t.USER_NOT_FOUND)
        return
    await state.clear()
    await _card(message, profile)


@router.message(F.text == t.BTN_ADMIN_USER)
async def btn_user(message: Message, state: FSMContext, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        return
    await _ask(message, state, action="view", prompt=t.ADMIN_PICK_VIEW)


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if not _guard(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    text = (command.args or "").strip()
    if not text:
        await state.set_state(AdminBroadcast.waiting_text)
        await answer_inline(message, t.ADMIN_BROADCAST_ASK, admin_pick_kb())
        return
    await _broadcast(bot, session, text, message)


@router.message(F.text == t.BTN_ADMIN_BROADCAST)
async def btn_broadcast(message: Message, state: FSMContext, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        return
    await state.set_state(AdminBroadcast.waiting_text)
    await answer_inline(message, t.ADMIN_BROADCAST_ASK, admin_pick_kb())


@router.message(AdminBroadcast.waiting_text, F.text)
async def broadcast_text(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
) -> None:
    if not _guard(message.from_user.id, config):
        await state.clear()
        return
    text = (message.text or "").strip()
    if text in t.MENU_BUTTONS or text in {t.BTN_CANCEL, t.BTN_BACK}:
        await message.answer(t.BROADCAST_IS_BUTTON)
        return
    if not text:
        await message.answer(t.BROADCAST_EMPTY)
        return
    await state.clear()
    await _broadcast(bot, session, text, message)


@router.message(Command("ban"))
async def cmd_ban(
    message: Message, command: CommandObject, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _guard(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    raw = (command.args or "").strip()
    if not raw:
        await _ask(message, state, action="ban", prompt=t.ADMIN_PICK_BAN)
        return
    profile = await _resolve(session, raw)
    if not profile or not profile.is_complete:
        await message.answer(t.USER_NOT_FOUND)
        return
    await _ban(message, session, profile, config, banned=True)


@router.message(F.text == t.BTN_ADMIN_BAN)
async def btn_ban(message: Message, state: FSMContext, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        return
    await _ask(message, state, action="ban", prompt=t.ADMIN_PICK_BAN)


@router.message(Command("unban"))
async def cmd_unban(
    message: Message, command: CommandObject, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _guard(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    raw = (command.args or "").strip()
    if not raw:
        await _ask(message, state, action="unban", prompt=t.ADMIN_PICK_UNBAN)
        return
    profile = await _resolve(session, raw)
    if not profile:
        await message.answer(t.USER_NOT_FOUND)
        return
    await _ban(message, session, profile, config, banned=False)


@router.message(F.text == t.BTN_ADMIN_UNBAN)
async def btn_unban(message: Message, state: FSMContext, config: Config) -> None:
    if not _guard(message.from_user.id, config):
        return
    await _ask(message, state, action="unban", prompt=t.ADMIN_PICK_UNBAN)


@router.message(AdminPickUser.waiting, F.text)
async def pick_text(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not _guard(message.from_user.id, config):
        await state.clear()
        return
    if message.text in t.MENU_BUTTONS:
        return
    data = await state.get_data()
    action = data.get("admin_action", "view")
    profile = await _resolve(session, message.text or "")
    if not profile or (action != "unban" and not profile.is_complete):
        await answer_inline(message, t.USER_NOT_FOUND, admin_pick_kb())
        return
    await state.clear()
    await _apply_action(message, session, config, profile, action if action in _ACTIONS else "view")
