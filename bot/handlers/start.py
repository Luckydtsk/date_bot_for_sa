from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.repositories import ProfileRepo
from bot.education import (
    BACHELOR_PROGRAMS,
    LEVEL_BACHELOR,
    LEVEL_MASTER,
    bachelor_programs_kb,
    course_kb,
    format_group,
    group_kb,
    level_kb,
)
from bot.keyboards.cleanup import clear_tracked_keyboards
from bot.config import Config
from bot.keyboards.common import (
    cancel_kb,
    dance_kb,
    gender_kb,
    menu_for,
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


async def _ask_edu_level(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_EDU_LEVEL, reply_markup=level_kb())
    await state.set_state(Registration.edu_level)


async def _ask_edu_program(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_EDU_PROGRAM, reply_markup=bachelor_programs_kb())
    await state.set_state(Registration.edu_program)


async def _ask_edu_course(message: Message, state: FSMContext) -> None:
    await message.answer(t.ASK_EDU_COURSE, reply_markup=course_kb())
    await state.set_state(Registration.edu_course)


async def _ask_edu_group(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    program = data["edu_program"]
    course = int(data["edu_course"])
    await message.answer(
        t.ASK_EDU_GROUP,
        reply_markup=group_kb(program, course),
    )
    await state.set_state(Registration.edu_group)


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


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config
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
        await message.answer(t.WELCOME_BACK, reply_markup=menu_for(message.from_user.id, config))
        if not message.from_user.username:
            await message.answer(t.USERNAME_MISSING_WARN)
        return

    await message.answer(t.WELCOME_NEW, reply_markup=remove_kb())
    await _ask_name(message, state)


@router.message(Registration.name, F.text)
async def reg_name(message: Message, state: FSMContext) -> None:
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
    await _ask_edu_level(message, state)


@router.message(Registration.edu_level, F.text)
async def reg_edu_level(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_gender(message, state)
        return
    if message.text == LEVEL_MASTER:
        await message.answer(t.MASTER_SOON, reply_markup=level_kb())
        return
    if message.text != LEVEL_BACHELOR:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=level_kb())
        return
    await state.update_data(edu_level=LEVEL_BACHELOR)
    await _ask_edu_program(message, state)


@router.message(Registration.edu_program, F.text)
async def reg_edu_program(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_edu_level(message, state)
        return
    program = (message.text or "").strip()
    if program not in BACHELOR_PROGRAMS:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=bachelor_programs_kb())
        return
    await state.update_data(edu_program=program)
    await _ask_edu_course(message, state)


@router.message(Registration.edu_course, F.text)
async def reg_edu_course(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_edu_program(message, state)
        return
    raw = (message.text or "").strip()
    if raw not in {"1", "2", "3", "4"}:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=course_kb())
        return
    await state.update_data(edu_course=int(raw))
    await _ask_edu_group(message, state)


@router.message(Registration.edu_group, F.text)
async def reg_edu_group(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_edu_course(message, state)
        return
    data = await state.get_data()
    program = data.get("edu_program")
    course = data.get("edu_course")
    if not program or not course:
        await _ask_edu_level(message, state)
        return
    allowed = {format_group(program, int(course), s) for s in (1, 2, 3, 4)}
    group = (message.text or "").strip()
    if group not in allowed:
        await message.answer(
            t.FSM_USE_BUTTONS,
            reply_markup=group_kb(program, int(course)),
        )
        return
    await state.update_data(faculty=group)
    await _ask_height(message, state)


@router.message(Registration.height, F.text)
async def reg_height(message: Message, state: FSMContext) -> None:
    if message.text == t.CANCEL:
        await _ask_edu_group(message, state)
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
async def reg_photo(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
) -> None:
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id, contact=None)
    await _finish_registration(message, state, session, config)


@router.message(Registration.photo)
async def reg_photo_invalid(message: Message) -> None:
    await message.answer(t.NEED_PHOTO, reply_markup=cancel_kb())


async def _finish_registration(
    message: Message, state: FSMContext, session: AsyncSession, config: Config
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
        contact=None,
        is_active=True,
    )
    await state.clear()
    await message.answer(t.REG_DONE, reply_markup=menu_for(message.from_user.id, config))
    await send_profile_card(message, profile, prefix=f"{t.MY_PROFILE_HEADER}\n\n")
    if not message.from_user.username:
        await message.answer(t.USERNAME_MISSING_WARN)
