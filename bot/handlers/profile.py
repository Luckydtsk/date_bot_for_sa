from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.db.repositories import ProfileRepo
from bot.keyboards.cleanup import clear_tracked_keyboards, track_keyboard_message
from bot.keyboards.common import (
    cancel_kb,
    dance_kb,
    edit_fields_kb,
    gender_kb,
    main_menu_kb,
    my_profile_kb,
    skip_cancel_kb,
    yes_no_kb,
)
from bot.services import DANCE_MAP, GENDER_MAP, opposite_gender, require_profile, send_profile_card
from bot.states.profile import EditProfile, Registration

router = Router(name="profile")


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


@router.message(StateFilter(default_state), F.text == t.BTN_MY_PROFILE)
async def my_profile(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await _show_my_profile(message, session, state)


@router.callback_query(F.data == "profile:menu")
async def back_menu(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.clear()
    await callback.message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "profile:pause")
async def pause_profile(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
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
    await callback.message.answer(t.PROFILE_PAUSED, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "profile:unpause")
async def unpause_profile(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
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
    await callback.message.answer(t.PROFILE_ACTIVE, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "profile:delete")
async def delete_ask(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.set_state(EditProfile.confirm_delete)
    await callback.message.answer(t.CONFIRM_DELETE, reply_markup=yes_no_kb())
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
async def delete_no(message: Message, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())


@router.callback_query(F.data == "profile:refill")
async def refill_ask(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.set_state(EditProfile.confirm_refill)
    await callback.message.answer(t.CONFIRM_REFILL, reply_markup=yes_no_kb())
    await callback.answer()


@router.message(EditProfile.confirm_refill, F.text == t.YES)
async def refill_yes(message: Message, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(t.ASK_NAME, reply_markup=cancel_kb())
    await state.set_state(Registration.name)


@router.message(EditProfile.confirm_refill, F.text == t.NO)
async def refill_no(message: Message, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())


@router.callback_query(F.data == "profile:edit")
async def edit_menu(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    await state.set_state(EditProfile.choose_field)
    sent = await callback.message.answer(t.CHOOSE_FIELD, reply_markup=edit_fields_kb())
    await track_keyboard_message(state, sent)
    await callback.answer()


@router.callback_query(EditProfile.choose_field, F.data.startswith("edit:"))
async def edit_field_pick(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(
        bot, callback.message.chat.id, state, also=callback.message
    )
    field = callback.data.split(":", 1)[1]
    mapping = {
        "name": (EditProfile.name, t.ASK_NAME, cancel_kb()),
        "gender": (EditProfile.gender, t.ASK_GENDER, gender_kb()),
        "faculty": (EditProfile.faculty, t.ASK_FACULTY, cancel_kb()),
        "height": (EditProfile.height, t.ASK_HEIGHT, skip_cancel_kb()),
        "dance": (EditProfile.dance, t.ASK_DANCE, dance_kb()),
        "about": (EditProfile.about, t.ASK_ABOUT, cancel_kb()),
        "photo": (EditProfile.photo, t.ASK_PHOTO, cancel_kb()),
        "contact": (EditProfile.contact, t.ASK_CONTACT, skip_cancel_kb()),
    }
    if field not in mapping:
        await callback.answer()
        return
    st, text, kb = mapping[field]
    await state.set_state(st)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


async def _after_edit(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(t.EDIT_DONE, reply_markup=main_menu_kb())
    await _show_my_profile(message, session, state)


@router.message(EditProfile.name, F.text)
async def edit_name(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
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
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.gender, F.text)
async def edit_gender(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
        return
    gender = GENDER_MAP.get(message.text or "")
    if not gender:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=gender_kb())
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
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.faculty, F.text)
async def edit_faculty(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
        return
    faculty = (message.text or "").strip()
    if not (2 <= len(faculty) <= 100):
        await message.answer(t.FACULTY_TOO_LONG if len(faculty) > 100 else t.NEED_TEXT)
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, faculty=faculty)
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.height, F.text)
async def edit_height(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
        return
    height = None
    if message.text != t.SKIP:
        raw = (message.text or "").strip().replace("см", "").strip()
        if not raw.isdigit() or not (100 <= int(raw) <= 250):
            await message.answer(t.INVALID_HEIGHT, reply_markup=skip_cancel_kb())
            return
        height = int(raw)
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, height=height)
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.dance, F.text)
async def edit_dance(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
        return
    dance = DANCE_MAP.get(message.text or "")
    if not dance:
        await message.answer(t.FSM_USE_BUTTONS, reply_markup=dance_kb())
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, dance_experience=dance)
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.about, F.text)
async def edit_about(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
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
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.photo, F.photo)
async def edit_photo(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, photo_file_id=message.photo[-1].file_id)
    await _after_edit(message, state, session, bot)


@router.message(EditProfile.photo, F.text == t.CANCEL)
async def edit_photo_cancel(message: Message, state: FSMContext, bot: Bot) -> None:
    await clear_tracked_keyboards(bot, message.chat.id, state)
    await state.clear()
    await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())


@router.message(EditProfile.photo)
async def edit_photo_invalid(message: Message) -> None:
    await message.answer(t.NEED_PHOTO, reply_markup=cancel_kb())


@router.message(EditProfile.contact, F.text)
async def edit_contact(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if message.text == t.CANCEL:
        await state.clear()
        await message.answer(t.MENU_TITLE, reply_markup=main_menu_kb())
        return
    contact = None if message.text == t.SKIP else (message.text or "").strip()
    if contact and len(contact) > 200:
        await message.answer("Слишком длинный контакт. До 200 символов.")
        return
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, contact=contact)
    await _after_edit(message, state, session, bot)
