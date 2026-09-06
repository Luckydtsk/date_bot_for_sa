from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
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
from bot.keyboards.cleanup import clear_tracked_keyboards, track_keyboard_message
from bot.keyboards.common import (
    cancel_kb,
    dance_kb,
    edit_fields_kb,
    gender_kb,
    is_admin,
    menu_for,
    my_profile_kb,
    remove_kb,
    skip_cancel_kb,
    with_main_menu,
    yes_no_kb,
)
from bot.services import DANCE_MAP, GENDER_MAP, opposite_gender, require_profile, send_profile_card
from bot.states.profile import EditProfile, Registration

router = Router(name="profile")


def _edit_kb(base: ReplyKeyboardMarkup, user_id: int, config: Config) -> ReplyKeyboardMarkup:
    return with_main_menu(base, is_admin=is_admin(user_id, config))


async def _show_my_profile(message: Message, session: AsyncSession, state: FSMContext) -> None:
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    sent = await send_profile_card(
        message,
        profile,
        prefix=f"{t.MY_PROFILE_HEADER}\n\n",
        reply_markup=my_profile_kb(is_paused=not profile.is_active),
    )
    await track_keyboard_message(state, sent)
    if not profile.is_active:
        await message.answer(t.PROFILE_PAUSED)


async def _show_edit_chooser(
    message: Message, state: FSMContext, config: Config
) -> None:
    """Список полей + возврат нижнего меню (на случай клавиатуры поля)."""
    await state.set_state(EditProfile.choose_field)
    await message.answer(
        t.CHOOSE_FIELD, reply_markup=menu_for(message.from_user.id, config)
    )
    sent = await message.answer("Выбери поле:", reply_markup=edit_fields_kb())
    await track_keyboard_message(state, sent)


async def _back_to_edit_chooser(
    message: Message, state: FSMContext, config: Config
) -> None:
    await _show_edit_chooser(message, state, config)


@router.message(StateFilter(default_state), F.text == t.BTN_MY_PROFILE)
async def my_profile(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await _show_my_profile(message, session, state)


@router.callback_query(F.data == "profile:menu")
async def back_menu(
    callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config
) -> None:
    if not callback.message:
        await callback.answer()
        return
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.clear()
    await callback.message.answer(
        t.MENU_TITLE, reply_markup=menu_for(callback.from_user.id, config)
    )
    await callback.answer()


@router.callback_query(F.data == "profile:pause")
async def pause_profile(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    repo = ProfileRepo(session)
    profile = await repo.get_by_tg(callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    await repo.set_paused(profile, True)
    await callback.message.answer(
        t.PROFILE_PAUSED, reply_markup=menu_for(callback.from_user.id, config)
    )
    await callback.answer()


@router.callback_query(F.data == "profile:unpause")
async def unpause_profile(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    repo = ProfileRepo(session)
    profile = await repo.get_by_tg(callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    await repo.set_paused(profile, False)
    await callback.message.answer(
        t.PROFILE_ACTIVE, reply_markup=menu_for(callback.from_user.id, config)
    )
    await callback.answer()


@router.callback_query(F.data == "profile:delete")
async def delete_ask(
    callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.set_state(EditProfile.confirm_delete)
    await callback.message.answer(
        t.CONFIRM_DELETE,
        reply_markup=_edit_kb(yes_no_kb(), callback.from_user.id, config),
    )
    await callback.answer()


@router.message(EditProfile.confirm_delete, F.text == t.YES)
async def delete_yes(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    repo = ProfileRepo(session)
    profile = await repo.get_by_tg(message.from_user.id)
    if profile:
        await repo.delete(profile)
    await state.clear()
    await message.answer(t.PROFILE_DELETED)


@router.message(EditProfile.confirm_delete, F.text == t.NO)
async def delete_no(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(
        t.MENU_TITLE, reply_markup=menu_for(message.from_user.id, config)
    )


@router.callback_query(F.data == "profile:refill")
async def refill_ask(
    callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.set_state(EditProfile.confirm_refill)
    await callback.message.answer(
        t.CONFIRM_REFILL,
        reply_markup=_edit_kb(yes_no_kb(), callback.from_user.id, config),
    )
    await callback.answer()


@router.message(EditProfile.confirm_refill, F.text == t.YES)
async def refill_yes(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    profile = await ProfileRepo(session).get_by_tg(message.from_user.id)
    if profile:
        # Скрываем из каталога; лайки/матчи сбросим только после успешного финиша
        await ProfileRepo(session).begin_refill(profile)
    await state.clear()
    await message.answer(t.ASK_NAME, reply_markup=remove_kb())
    await state.set_state(Registration.name)


@router.message(EditProfile.confirm_refill, F.text == t.NO)
async def refill_no(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(
        t.MENU_TITLE, reply_markup=menu_for(message.from_user.id, config)
    )


@router.callback_query(F.data == "profile:edit")
async def edit_menu(
    callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await _show_edit_chooser(callback.message, state, config)
    await callback.answer()


@router.message(StateFilter(EditProfile), F.text == t.BTN_BROWSE)
async def edit_abort_browse(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    from bot.handlers.feed import start_browse

    await start_browse(message, state, session, bot, config)


@router.message(StateFilter(EditProfile), F.text == t.BTN_MY_PROFILE)
async def edit_abort_my_profile(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await _show_my_profile(message, session, state)


@router.message(StateFilter(EditProfile), F.text == t.BTN_LIKES_ME)
async def edit_abort_likes_me(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    from bot.handlers.likes import start_likes_me

    await start_likes_me(message, state, session, bot, config)


@router.message(StateFilter(EditProfile), F.text == t.BTN_ADMIN)
async def edit_abort_admin(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    from bot.handlers.admin import open_admin_panel

    await open_admin_panel(message, state, bot, config)


@router.callback_query(EditProfile.choose_field, F.data.startswith("edit:"))
async def edit_field_pick(
    callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    field = callback.data.split(":", 1)[1]
    uid = callback.from_user.id
    mapping = {
        "name": (EditProfile.name, t.ASK_NAME, _edit_kb(cancel_kb(), uid, config)),
        "gender": (EditProfile.gender, t.ASK_GENDER, _edit_kb(gender_kb(), uid, config)),
        "faculty": (
            EditProfile.edu_level,
            t.ASK_EDU_LEVEL,
            _edit_kb(level_kb(), uid, config),
        ),
        "height": (
            EditProfile.height,
            t.ASK_HEIGHT,
            _edit_kb(skip_cancel_kb(), uid, config),
        ),
        "dance": (EditProfile.dance, t.ASK_DANCE, _edit_kb(dance_kb(), uid, config)),
        "about": (EditProfile.about, t.ASK_ABOUT, _edit_kb(cancel_kb(), uid, config)),
        "photo": (EditProfile.photo, t.ASK_PHOTO, _edit_kb(cancel_kb(), uid, config)),
    }
    if field not in mapping:
        await callback.answer()
        return
    st, text, kb = mapping[field]
    await state.set_state(st)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


async def _after_edit(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(
        t.EDIT_DONE, reply_markup=menu_for(message.from_user.id, config)
    )
    await _show_my_profile(message, session, state)


@router.message(EditProfile.name, F.text)
async def edit_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if message.text == t.CANCEL:
        await _back_to_edit_chooser(message, state, config)
        return
    name = (message.text or "").strip()
    if not (1 <= len(name) <= 50):
        await message.answer(t.NAME_TOO_LONG if len(name) > 50 else t.NEED_TEXT)
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, name=name)
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.gender, F.text)
async def edit_gender(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if message.text == t.CANCEL:
        await _back_to_edit_chooser(message, state, config)
        return
    gender = GENDER_MAP.get(message.text or "")
    if not gender:
        await message.answer(
            t.FSM_USE_BUTTONS,
            reply_markup=_edit_kb(gender_kb(), message.from_user.id, config),
        )
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(
        profile,
        gender=gender,
        looking_for=opposite_gender(gender),
    )
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.edu_level, F.text)
async def edit_edu_level(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    uid = message.from_user.id
    if message.text == t.CANCEL:
        await _back_to_edit_chooser(message, state, config)
        return
    if message.text == LEVEL_MASTER:
        await message.answer(
            t.MASTER_SOON, reply_markup=_edit_kb(level_kb(), uid, config)
        )
        return
    if message.text != LEVEL_BACHELOR:
        await message.answer(
            t.FSM_USE_BUTTONS, reply_markup=_edit_kb(level_kb(), uid, config)
        )
        return
    await state.update_data(edu_level=LEVEL_BACHELOR)
    await message.answer(
        t.ASK_EDU_PROGRAM,
        reply_markup=_edit_kb(bachelor_programs_kb(), uid, config),
    )
    await state.set_state(EditProfile.edu_program)


@router.message(EditProfile.edu_program, F.text)
async def edit_edu_program(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    uid = message.from_user.id
    if message.text == t.CANCEL:
        await message.answer(
            t.ASK_EDU_LEVEL, reply_markup=_edit_kb(level_kb(), uid, config)
        )
        await state.set_state(EditProfile.edu_level)
        return
    program = (message.text or "").strip()
    if program not in BACHELOR_PROGRAMS:
        await message.answer(
            t.FSM_USE_BUTTONS,
            reply_markup=_edit_kb(bachelor_programs_kb(), uid, config),
        )
        return
    await state.update_data(edu_program=program)
    await message.answer(
        t.ASK_EDU_COURSE, reply_markup=_edit_kb(course_kb(), uid, config)
    )
    await state.set_state(EditProfile.edu_course)


@router.message(EditProfile.edu_course, F.text)
async def edit_edu_course(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    uid = message.from_user.id
    if message.text == t.CANCEL:
        await message.answer(
            t.ASK_EDU_PROGRAM,
            reply_markup=_edit_kb(bachelor_programs_kb(), uid, config),
        )
        await state.set_state(EditProfile.edu_program)
        return
    raw = (message.text or "").strip()
    if raw not in {"1", "2", "3", "4"}:
        await message.answer(
            t.FSM_USE_BUTTONS, reply_markup=_edit_kb(course_kb(), uid, config)
        )
        return
    await state.update_data(edu_course=int(raw))
    data = await state.get_data()
    program = data["edu_program"]
    await message.answer(
        t.ASK_EDU_GROUP,
        reply_markup=_edit_kb(group_kb(program, int(raw)), uid, config),
    )
    await state.set_state(EditProfile.edu_group)


@router.message(EditProfile.edu_group, F.text)
async def edit_edu_group(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    uid = message.from_user.id
    data = await state.get_data()
    program = data.get("edu_program")
    course = data.get("edu_course")
    if message.text == t.CANCEL:
        await message.answer(
            t.ASK_EDU_COURSE, reply_markup=_edit_kb(course_kb(), uid, config)
        )
        await state.set_state(EditProfile.edu_course)
        return
    if not program or not course:
        await message.answer(
            t.ASK_EDU_LEVEL, reply_markup=_edit_kb(level_kb(), uid, config)
        )
        await state.set_state(EditProfile.edu_level)
        return
    allowed = {format_group(program, int(course), s) for s in (1, 2, 3, 4)}
    group = (message.text or "").strip()
    if group not in allowed:
        await message.answer(
            t.FSM_USE_BUTTONS,
            reply_markup=_edit_kb(group_kb(program, int(course)), uid, config),
        )
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, faculty=group)
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.height, F.text)
async def edit_height(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if message.text == t.CANCEL:
        await _back_to_edit_chooser(message, state, config)
        return
    height = None
    if message.text != t.SKIP:
        raw = (message.text or "").strip().replace("см", "").strip()
        if not raw.isdigit() or not (100 <= int(raw) <= 250):
            await message.answer(
                t.INVALID_HEIGHT,
                reply_markup=_edit_kb(skip_cancel_kb(), message.from_user.id, config),
            )
            return
        height = int(raw)
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, height=height)
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.dance, F.text)
async def edit_dance(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if message.text == t.CANCEL:
        await _back_to_edit_chooser(message, state, config)
        return
    dance = DANCE_MAP.get(message.text or "")
    if not dance:
        await message.answer(
            t.FSM_USE_BUTTONS,
            reply_markup=_edit_kb(dance_kb(), message.from_user.id, config),
        )
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, dance_experience=dance)
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.about, F.text)
async def edit_about(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    if message.text == t.CANCEL:
        await _back_to_edit_chooser(message, state, config)
        return
    about = (message.text or "").strip()
    if len(about) < 5:
        await message.answer(t.ABOUT_TOO_SHORT)
        return
    if len(about) > 400:
        await message.answer(t.ABOUT_TOO_LONG)
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, about=about)
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.photo, F.photo)
async def edit_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    config: Config,
) -> None:
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(
        profile, photo_file_id=message.photo[-1].file_id
    )
    await _after_edit(message, state, session, bot, config)


@router.message(EditProfile.photo, F.text == t.CANCEL)
async def edit_photo_cancel(
    message: Message, state: FSMContext, bot: Bot, config: Config
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await _back_to_edit_chooser(message, state, config)


@router.message(EditProfile.photo)
async def edit_photo_invalid(message: Message, config: Config) -> None:
    await message.answer(
        t.NEED_PHOTO,
        reply_markup=_edit_kb(cancel_kb(), message.from_user.id, config),
    )


@router.message(StateFilter(EditProfile))
async def edit_unexpected(message: Message) -> None:
    await message.answer(t.FSM_NEED_TEXT)
