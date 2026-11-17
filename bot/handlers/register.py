"""Анкета с номером шага, «Назад» и «Отмена»."""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.repositories import ProfileRepo
from bot.education import LEVEL_BACHELOR, LEVEL_MASTER, level_kb
from bot.keyboards.common import (
    back_cancel_kb,
    cancel_kb,
    dance_kb,
    gender_kb,
    menu_for,
    skip_back_kb,
)
from bot.services import (
    DANCE_MAP,
    GENDER_MAP,
    deliver_photo,
    opposite_gender,
    parse_height,
)
from bot.states.profile import Registration

router = Router(name="register")

DEFAULT_GOAL = "full_evening"


async def begin(message: Message, state: FSMContext, *, refill: bool) -> None:
    total = 8 if message.from_user.username else 9
    await state.set_data({"refill": refill, "steps_total": total})
    await _ask_name(message, state)


async def _total(state: FSMContext) -> int:
    data = await state.get_data()
    return int(data.get("steps_total") or 10)


async def _ask_name(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(1, total, t.ASK_NAME_TITLE, t.ASK_NAME_BODY, back=False),
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(Registration.name)


async def _ask_gender(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(2, total, t.ASK_GENDER_TITLE, t.ASK_GENDER_BODY, back=True),
        parse_mode="HTML",
        reply_markup=gender_kb(),
    )
    await state.set_state(Registration.gender)


async def _ask_level(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(3, total, t.ASK_LEVEL_TITLE, t.ASK_LEVEL_BODY, back=True),
        parse_mode="HTML",
        reply_markup=level_kb(),
    )
    await state.set_state(Registration.edu_level)


async def _ask_faculty(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(4, total, t.ASK_FACULTY_TITLE, t.ASK_FACULTY_BODY, back=True),
        parse_mode="HTML",
        reply_markup=back_cancel_kb(),
    )
    await state.set_state(Registration.faculty)


async def _ask_height(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(5, total, t.ASK_HEIGHT_TITLE, t.ASK_HEIGHT_BODY, back=True),
        parse_mode="HTML",
        reply_markup=skip_back_kb(),
    )
    await state.set_state(Registration.height)


async def _ask_dance(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(6, total, t.ASK_DANCE_TITLE, t.ASK_DANCE_BODY, back=True),
        parse_mode="HTML",
        reply_markup=dance_kb(),
    )
    await state.set_state(Registration.dance)


async def _ask_about(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(7, total, t.ASK_ABOUT_TITLE, t.ASK_ABOUT_BODY, back=True),
        parse_mode="HTML",
        reply_markup=back_cancel_kb(),
    )
    await state.set_state(Registration.about)


async def _ask_photo(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(8, total, t.ASK_PHOTO_TITLE, t.ASK_PHOTO_BODY, back=True),
        parse_mode="HTML",
        reply_markup=back_cancel_kb(),
    )
    await state.set_state(Registration.photo)


async def _ask_contact(message: Message, state: FSMContext) -> None:
    total = await _total(state)
    await message.answer(
        t.step(9, total, t.ASK_CONTACT_TITLE, t.ASK_CONTACT_BODY, back=True),
        parse_mode="HTML",
        reply_markup=skip_back_kb(),
    )
    await state.set_state(Registration.contact)


@router.message(Registration.name, F.text)
async def reg_name(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
        await message.answer("Это первый шаг. «Отмена» — выйти.")
        return
    name = (message.text or "").strip()
    if name in t.RESERVED_INPUTS:
        await message.answer(t.NAME_IS_BUTTON)
        return
    if not name:
        await message.answer(t.NAME_EMPTY)
        return
    if len(name) > 50:
        await message.answer(t.NAME_TOO_LONG)
        return
    await state.update_data(name=name)
    await _ask_gender(message, state)


@router.message(Registration.gender, F.text)
async def reg_gender(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
        await _ask_name(message, state)
        return
    gender = GENDER_MAP.get(message.text or "")
    if not gender:
        await message.answer(t.USE_BUTTONS, reply_markup=gender_kb())
        return
    await state.update_data(gender=gender, looking_for=opposite_gender(gender))
    await _ask_level(message, state)


@router.message(Registration.edu_level, F.text)
async def reg_level(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
        await _ask_gender(message, state)
        return
    if message.text == LEVEL_MASTER:
        await message.answer(t.MASTER_SOON, reply_markup=level_kb())
        return
    if message.text != LEVEL_BACHELOR:
        await message.answer(t.USE_BUTTONS, reply_markup=level_kb())
        return
    await state.update_data(edu_level=LEVEL_BACHELOR)
    await _ask_faculty(message, state)


@router.message(Registration.faculty, F.text)
async def reg_faculty(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
        await _ask_level(message, state)
        return
    faculty = (message.text or "").strip()
    if faculty in t.RESERVED_INPUTS or faculty in {LEVEL_BACHELOR, LEVEL_MASTER}:
        await message.answer(t.FACULTY_BAD, reply_markup=back_cancel_kb())
        return
    if not faculty or len(faculty) > 100:
        await message.answer(t.FACULTY_BAD, reply_markup=back_cancel_kb())
        return
    await state.update_data(faculty=faculty)
    await _ask_height(message, state)


@router.message(Registration.height, F.text)
async def reg_height(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
        await _ask_faculty(message, state)
        return
    if message.text == t.SKIP:
        await state.update_data(height=None)
    else:
        height = parse_height(message.text or "")
        if height is None:
            await message.answer(t.INVALID_HEIGHT, reply_markup=skip_back_kb())
            return
        await state.update_data(height=height)
    await _ask_dance(message, state)


@router.message(Registration.dance, F.text)
async def reg_dance(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
        await _ask_height(message, state)
        return
    dance = DANCE_MAP.get(message.text or "")
    if not dance:
        await message.answer(t.USE_BUTTONS, reply_markup=dance_kb())
        return
    await state.update_data(dance_experience=dance, goal=DEFAULT_GOAL)
    await _ask_about(message, state)


@router.message(Registration.about, F.text)
async def reg_about(message: Message, state: FSMContext) -> None:
    if message.text == t.BTN_BACK:
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


@router.message(Registration.photo, F.text == t.BTN_BACK)
async def reg_photo_back(message: Message, state: FSMContext) -> None:
    await _ask_about(message, state)


@router.message(Registration.photo, F.photo)
async def reg_photo(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    if message.from_user.username:
        await state.update_data(contact=None)
        await _finish(message, state, session, config)
        return
    await _ask_contact(message, state)


@router.message(Registration.photo)
async def reg_photo_invalid(message: Message) -> None:
    await message.answer(t.NEED_PHOTO, reply_markup=back_cancel_kb())


@router.message(Registration.contact, F.text)
async def reg_contact(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    if message.text == t.BTN_BACK:
        await _ask_photo(message, state)
        return
    if message.text == t.SKIP:
        await state.update_data(contact=None)
    else:
        contact = (message.text or "").strip()
        if not contact:
            await message.answer(t.NEED_TEXT)
            return
        if len(contact) > 200:
            await message.answer(t.CONTACT_TOO_LONG, reply_markup=skip_back_kb())
            return
        await state.update_data(contact=contact)
    await _finish(message, state, session, config)


@router.message(StateFilter(Registration))
async def reg_unexpected(message: Message) -> None:
    await message.answer(t.NEED_TEXT)


async def _finish(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    data = await state.get_data()
    needed = (
        "name",
        "gender",
        "looking_for",
        "faculty",
        "dance_experience",
        "about",
        "photo_file_id",
    )
    if any(not data.get(key) for key in needed):
        await message.answer("Анкета собралась не до конца. Нажми «Старт» и начнём с имени.")
        await state.clear()
        return
    fresh = await ProfileRepo(session).get_by_tg(message.from_user.id) is None
    profile = await ProfileRepo(session).upsert_complete(
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
    await message.answer(
        t.REG_DONE,
        parse_mode="HTML",
        reply_markup=menu_for(message.from_user.id, config),
    )
    await deliver_photo(
        message,
        profile.photo_file_id,
        f"<b>Так тебя видят</b>\n\n{t.format_card(profile)}",
    )
    if not message.from_user.username:
        await message.answer(t.USERNAME_HINT)
    if fresh:
        from bot.services import _who, notify_admins

        await notify_admins(
            message.bot,
            session,
            t.NOTIFY_NEW.format(who=_who(profile)),
            skip={message.from_user.id},
        )
