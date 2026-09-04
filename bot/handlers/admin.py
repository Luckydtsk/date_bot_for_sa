from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.repositories import ProfileRepo, StatsRepo
from bot.states.profile import AdminBroadcast

router = Router(name="admin")


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


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
