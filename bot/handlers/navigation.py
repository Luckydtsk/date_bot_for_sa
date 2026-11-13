"""Меню, /start, /help, /cancel. Срабатывает из любого шага."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.repositories import ProfileRepo
from bot.handlers.feed import open_feed
from bot.handlers.likes import open_likes
from bot.handlers.pairs import open_pairs
from bot.handlers.profile import open_my_profile
from bot.handlers.register import begin
from bot.keyboards.common import is_admin, menu_for, remove_kb
from bot.services import require_profile, touch_username

router = Router(name="navigation")


def _leave_note(state_name: str | None, data: dict) -> str | None:
    if data.get("refill"):
        return t.REFILL_CANCELLED
    if state_name and state_name.startswith("Registration"):
        return t.REG_CANCELLED
    if state_name and state_name.startswith("EditProfile"):
        return t.EDIT_CANCELLED
    if state_name and state_name.startswith("Admin"):
        return t.ADMIN_STEP_CANCELLED
    return None


async def _ready(
    message: Message, state: FSMContext, session: AsyncSession
) -> bool:
    profile = await require_profile(session, message.from_user.id)
    if profile:
        return True
    await message.answer(t.FINISH_FIRST, parse_mode="HTML")
    return False


async def _open_section(
    message: Message, state: FSMContext, session: AsyncSession
) -> bool:
    """Выход из текущего шага в раздел меню. Без анкеты шаг не прерываем."""
    if not await _ready(message, state, session):
        return False
    data = await state.get_data()
    note = _leave_note(await state.get_state(), data)
    await state.clear()
    if note:
        await message.answer(note, parse_mode="HTML")
    return True


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    await state.clear()
    repo = ProfileRepo(session)
    profile = await repo.get_by_tg(message.from_user.id)
    if profile and profile.is_banned and message.from_user.id not in config.admin_ids:
        await message.answer(t.PROFILE_BANNED)
        return
    if profile and profile.is_complete:
        await touch_username(session, profile, message.from_user.username)
        await message.answer(
            t.welcome_back(profile.name),
            parse_mode="HTML",
            reply_markup=menu_for(message.from_user.id, config),
        )
        return
    if profile:
        await message.answer(t.CONTINUE_HIDDEN, parse_mode="HTML")
        await begin(message, state, refill=True)
        return
    await message.answer(t.HELP_FULL, parse_mode="HTML")
    await message.answer(t.REG_INTRO, parse_mode="HTML")
    await begin(message, state, refill=False)


@router.message(Command("help"))
@router.message(F.text == t.BTN_HELP)
async def cmd_help(message: Message, state: FSMContext, session: AsyncSession, config: Config) -> None:
    profile = await require_profile(session, message.from_user.id)
    data = await state.get_data()
    state_name = await state.get_state()
    extra = ""
    if data.get("refill"):
        extra = t.HELP_WHILE_REFILL
    elif state_name and state_name.startswith("Registration"):
        extra = t.HELP_WHILE_REG
    text = t.HELP_FULL + extra
    if profile:
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=menu_for(message.from_user.id, config),
        )
        return
    await message.answer(text, parse_mode="HTML")


@router.message(Command("cancel"))
@router.message(F.text == t.BTN_CANCEL)
async def cmd_cancel(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    data = await state.get_data()
    state_name = await state.get_state()
    note = _leave_note(state_name, data)
    await state.clear()
    profile = await require_profile(session, message.from_user.id)
    if profile:
        await message.answer(
            note or t.ALREADY_IDLE,
            parse_mode="HTML",
            reply_markup=menu_for(message.from_user.id, config),
        )
        return
    await message.answer(note or t.REG_CANCELLED, parse_mode="HTML", reply_markup=remove_kb())


@router.message(F.text.in_({t.BTN_BROWSE, t.ALIAS_BROWSE}))
async def menu_browse(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not await _open_section(message, state, session):
        return
    await open_feed(message, session, config)


@router.message(F.text == t.BTN_LIKES_ME)
async def menu_likes(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not await _open_section(message, state, session):
        return
    await open_likes(message, session, config)


@router.message(F.text == t.BTN_MATCHES)
async def menu_pairs(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not await _open_section(message, state, session):
        return
    await open_pairs(message, session, config)


@router.message(F.text == t.BTN_MY_PROFILE)
async def menu_profile(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not await _open_section(message, state, session):
        return
    await open_my_profile(message, session, config)


@router.message(F.text == t.BTN_ADMIN)
@router.message(Command("admin"))
async def menu_admin(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        await message.answer(t.ADMIN_ONLY)
        return
    await state.clear()
    from bot.handlers.admin import open_admin_panel

    await open_admin_panel(message, config)
    if message.text and message.text.startswith("/admin"):
        await message.answer(t.ADMIN_HELP)


@router.message(F.text == t.BTN_ADMIN_BACK)
async def old_admin_back(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    await state.clear()
    profile = await require_profile(session, message.from_user.id)
    text = t.welcome_back(profile.name) if profile else t.ALREADY_IDLE
    markup = menu_for(message.from_user.id, config) if profile else remove_kb()
    await message.answer(text, parse_mode="HTML", reply_markup=markup)
