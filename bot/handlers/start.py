from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.repositories import ProfileRepo
from bot.keyboards.cleanup import clear_tracked_keyboards
from bot.keyboards.common import (
    cancel_kb,
    dance_kb,
    gender_kb,
    main_menu_kb,
    remove_kb,
    skip_cancel_kb,
)
from bot.services import DANCE_MAP, GENDER_MAP, opposite_gender, send_profile_card
from bot.states.profile import Registration

router = Router(name="start")

DEFAULT_GOAL = "full_evening"


async def _ask_name(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_NAME, reply_markup=remove_kb())
    await state.set_state(Registration.name)


async def _ask_gender(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_GENDER, reply_markup=gender_kb())
    await state.set_state(Registration.gender)


async def _ask_faculty(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_FACULTY, reply_markup=cancel_kb())
    await state.set_state(Registration.faculty)


async def _ask_height(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_HEIGHT, reply_markup=skip_cancel_kb())
    await state.set_state(Registration.height)


async def _ask_dance(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_DANCE, reply_markup=dance_kb())
    await state.set_state(Registration.dance)


async def _ask_about(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_ABOUT, reply_markup=cancel_kb())
    await state.set_state(Registration.about)


async def _ask_photo(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_PHOTO, reply_markup=cancel_kb())
    await state.set_state(Registration.photo)


async def _ask_contact(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_CONTACT, reply_markup=skip_cancel_kb())
    await state.set_state(Registration.contact)


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    repo = ProfileRepo(session)
    profile = await repo.get_by_tg(message.from_user.id)

    if profile and profile.is_banned:
        await message.answer(t.PROFILE_BANNED)
        return

    if profile and profile.is_complete:
        await repo.sync_username(profile, message.from_user.username)
        await message.answer(t.WELCOME_BACK, reply_markup=main_menu_kb())
        if not message.from_user.username and not profile.contact:
            await message.answer(t.USERNAME_MISSING_WARN)
        return

    await message.answer(t.WELCOME_NEW, reply_markup=remove_kb())
    await _ask_name(message, state)


@router.message(Registration.name, F.text)
async def reg_name(message: Message, state: FSMContext) -> None:
    # На шаге имени «Отмена» не предлагаем — если вдруг прислали, просто просим имя
    if message.text == t.CANCEL:
        await message.answer(t.ASK_NAME, reply_markup=remove_kb())
        return
    name = (message.text or "").strip()
    if len(name) < 1:
        await message.answer(t.NEED_TEXT)
        return
    if len(name) > 50:
        await message.answer(t.NAME_TOO_LONG)
        return
    await state.update_data(name=name)
    await _ask_gender(message, state)


@router.message(Registration.gender, F.text)
async def reg_gender(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_name(message, state)
        return
    gender = GENDER_MAP.get(message.text or "")
    if not gender:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=gender_kb())
        return
    await state.update_data(gender=gender, looking_for=opposite_gender(gender))
    await _ask_faculty(message, state)


@router.message(Registration.faculty, F.text)
async def reg_faculty(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_gender(message, state)
        return
    faculty = (message.text or "").strip()
    if len(faculty) < 2:
        await message.answer(t.NEED_TEXT)
        return
    if len(faculty) > 100:
        await message.answer(t.FACULTY_TOO_LONG)
        return
    await state.update_data(faculty=faculty)
    await _ask_height(message, state)


@router.message(Registration.height, F.text)
async def reg_height(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_faculty(message, state)
        return
    if message.text == t.SKIP:
        await state.update_data(height=None)
    else:
        raw = (message.text or "").strip().replace("см", "").strip()
        if not raw.isdigit() or not (100 <= int(raw) <= 250):
            await message.answer(t.INVALID_HEIGHT, reply_markup=skip_cancel_kb())
            return
        await state.update_data(height=int(raw))
    await _ask_dance(message, state)


@router.message(Registration.dance, F.text)
async def reg_dance(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_height(message, state)
        return
    dance = DANCE_MAP.get(message.text or "")
    if not dance:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=dance_kb())
        return
    await state.update_data(dance_experience=dance, goal=DEFAULT_GOAL)
    await _ask_about(message, state)


@router.message(Registration.about, F.text)
async def reg_about(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_dance(message, state)
        return
    about = (message.text or "").strip()
    if len(about) < 5:
        await message.answer(t.ABOUT_TOO_SHORT)
        return
    if len(about) > 400:
        await message.answer(t.ABOUT_TOO_LONG)
        return
    await state.update_data(about=about)
    await _ask_photo(message, state)


@router.message(Registration.photo, F.text == t.CANCEL)
async def reg_photo_cancel(message: Message, state: FSMContext) -> None:
    await _ask_about(message, state)


@router.message(Registration.photo, F.photo)
async def reg_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)

    if message.from_user.username:
        await state.update_data(contact=None)
        await _finish_registration(message, state, session)
        return

    await _ask_contact(message, state)


@router.message(Registration.photo)
async def reg_photo_invalid(message: Message) -> None:
    await message.answer(t.NEED_PHOTO, reply_markup=cancel_kb())


@router.message(Registration.contact, F.text)
async def reg_contact(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.text == t.CANCEL:
        await _ask_photo(message, state)
        return
    if message.text == t.SKIP:
        await state.update_data(contact=None)
    else:
        contact = (message.text or "").strip()
        if len(contact) > 200:
            await message.answer("Слишком длинный контакт. До 200 символов.")
            return
        await state.update_data(contact=contact)
    await _finish_registration(message, state, session)


async def _finish_registration(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    repo = ProfileRepo(session)
    profile = await repo.upsert_complete(
        message.from_user.id,
        username=message.from_user.username,
        name=data["name"],
        gender=data["gender"],
        looking_for=data["looking_for"],
        faculty=data["faculty"],
        height=data.get("height"),
        dance_experience=data["dance_experience"],
        goal=data.get("goal", DEFAULT_GOAL),
        about=data["about"],
        photo_file_id=data["photo_file_id"],
        contact=data.get("contact"),
        is_active=True,
    )
    await state.clear()
    await message.answer(t.REG_DONE, reply_markup=main_menu_kb())
    await send_profile_card(message, profile, prefix=f"{t.MY_PROFILE_HEADER}\n\n")
    if not message.from_user.username and not profile.contact:
        await message.answer(t.USERNAME_MISSING_WARN)
