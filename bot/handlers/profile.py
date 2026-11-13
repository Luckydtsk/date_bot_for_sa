"""Своя анкета: правки не прячут меню внизу."""

import html

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.repositories import ProfileRepo
from bot.education import (
    BACHELOR_PROGRAMS,
    LEVEL_BACHELOR,
    course_inline,
    format_group,
    group_inline,
    level_inline,
    programs_inline,
)
from bot.handlers.register import begin
from bot.keyboards.common import (
    confirm_kb,
    dance_inline,
    edit_fields_kb,
    gender_inline,
    height_edit_kb,
    keep_kb,
    menu_for,
    my_profile_kb,
    remove_kb,
)
from bot.services import deliver_photo, opposite_gender, parse_height, require_profile
from bot.states.profile import EditProfile

router = Router(name="profile")


async def open_my_profile(message: Message, session: AsyncSession, config: Config) -> None:
    profile = await require_profile(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE, reply_markup=menu_for(message.from_user.id, config))
        return
    await message.answer(
        "Так тебя видят другие. Под фото можно изменить, скрыть или удалить.",
        reply_markup=menu_for(message.from_user.id, config),
    )
    await deliver_photo(
        message,
        profile.photo_file_id,
        t.my_profile_caption(profile),
        my_profile_kb(paused=not profile.is_active),
    )


async def _profile_for_edit(session: AsyncSession, user_id: int):
    return await require_profile(session, user_id)


async def _remember_card(state: FSMContext, message: Message) -> None:
    await state.update_data(card_chat_id=message.chat.id, card_message_id=message.message_id)


async def _refresh_card(bot: Bot, state: FSMContext, session: AsyncSession, user_id: int) -> None:
    profile = await _profile_for_edit(session, user_id)
    data = await state.get_data()
    chat_id = data.get("card_chat_id")
    message_id = data.get("card_message_id")
    if profile is None or not chat_id or not message_id:
        return
    from aiogram.types import InputMediaPhoto

    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=profile.photo_file_id,
                caption=t.my_profile_caption(profile),
                parse_mode="HTML",
            ),
            reply_markup=my_profile_kb(paused=not profile.is_active),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            await bot.send_photo(
                chat_id,
                photo=profile.photo_file_id,
                caption=t.my_profile_caption(profile),
                parse_mode="HTML",
                reply_markup=my_profile_kb(paused=not profile.is_active),
            )


async def _set_card_markup(bot: Bot, state: FSMContext, markup: InlineKeyboardMarkup | None) -> None:
    data = await state.get_data()
    chat_id = data.get("card_chat_id")
    message_id = data.get("card_message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=markup
        )
    except Exception:
        pass


async def _show_fields(bot: Bot, state: FSMContext) -> None:
    await state.set_state(EditProfile.choose_field)
    await _set_card_markup(bot, state, edit_fields_kb())


def _prompt(title: str, body: str, current: str | None = None) -> str:
    lines = [f"<b>{html.escape(title)}</b>", html.escape(body)]
    if current:
        lines.append(f"Сейчас: {html.escape(current)}")
    lines.append(f"{t.EDIT_KEEP} — под этим сообщением. /cancel — в меню.")
    return "\n".join(lines)


@router.callback_query(F.data == "profile:edit")
async def edit_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if callback.message is None:
        await callback.answer()
        return
    if not await _profile_for_edit(session, callback.from_user.id):
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    await _remember_card(state, callback.message)
    await _show_fields(bot, state)
    await callback.answer(t.CHOOSE_FIELD)


@router.callback_query(F.data == "edit:back")
async def edit_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    if callback.message is None:
        await callback.answer()
        return
    current = await state.get_state()
    if current in {None, EditProfile.choose_field.state}:
        profile = await _profile_for_edit(session, callback.from_user.id)
        if profile and callback.message.photo:
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=my_profile_kb(paused=not profile.is_active)
                )
            except Exception:
                pass
        elif profile:
            await _set_card_markup(bot, state, my_profile_kb(paused=not profile.is_active))
        await state.clear()
        await callback.answer()
        return

    await _show_fields(bot, state)
    if callback.message.photo:
        await callback.answer("Не менял")
        return
    try:
        await callback.message.edit_text("Не менял.", reply_markup=None)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "profile:pause")
@router.callback_query(F.data == "profile:unpause")
async def toggle_pause(
    callback: CallbackQuery, session: AsyncSession, config: Config
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    repo = ProfileRepo(session)
    profile = await _profile_for_edit(session, callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    paused = callback.data == "profile:pause"
    await repo.set_paused(profile, paused)
    caption = t.my_profile_caption(profile)
    markup = my_profile_kb(paused=paused)
    try:
        await callback.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=markup)
    except Exception:
        await deliver_photo(callback.message, profile.photo_file_id, caption, markup)
    await callback.message.answer(
        t.PROFILE_PAUSED if paused else t.PROFILE_ACTIVE,
        reply_markup=menu_for(callback.from_user.id, config),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:delete")
async def delete_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await _profile_for_edit(session, callback.from_user.id):
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    if callback.message:
        await callback.message.answer(t.CONFIRM_DELETE, reply_markup=confirm_kb("del"))
    await callback.answer()


@router.callback_query(F.data == "profile:refill")
async def refill_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await _profile_for_edit(session, callback.from_user.id):
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    if callback.message:
        await callback.message.answer(t.CONFIRM_REFILL, reply_markup=confirm_kb("refill"))
    await callback.answer()


@router.callback_query(F.data == "ask:del:no")
@router.callback_query(F.data == "ask:refill:no")
async def ask_no(callback: CallbackQuery) -> None:
    if callback.message:
        try:
            await callback.message.edit_text("Ок, анкета на месте.", reply_markup=None)
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data == "ask:del:yes")
async def delete_yes(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    repo = ProfileRepo(session)
    profile = await repo.get_by_tg(callback.from_user.id)
    if profile:
        await repo.delete(profile)
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(t.PROFILE_DELETED, reply_markup=remove_kb())
    await callback.answer()


@router.callback_query(F.data == "ask:refill:yes")
async def refill_yes(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    profile = await ProfileRepo(session).get_by_tg(callback.from_user.id)
    if profile:
        await ProfileRepo(session).begin_refill(profile)
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer()
    await begin(callback.message, state, refill=True)


@router.callback_query(F.data.startswith("edit:"), ~F.data.in_({"edit:back", "edit:height:clear"}))
async def edit_pick(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    field = (callback.data or "").split(":", 1)[1]
    if field == "back":
        await callback.answer()
        return
    profile = await _profile_for_edit(session, callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    if callback.message.photo:
        await _remember_card(state, callback.message)
    await _set_card_markup(bot, state, keep_kb())

    if field == "name":
        await state.set_state(EditProfile.name)
        await callback.message.answer(
            _prompt("Имя", t.EDIT_NAME, profile.name),
            parse_mode="HTML",
            reply_markup=keep_kb(),
        )
    elif field == "about":
        await state.set_state(EditProfile.about)
        await callback.message.answer(
            _prompt("О себе", t.EDIT_ABOUT, profile.about),
            parse_mode="HTML",
            reply_markup=keep_kb(),
        )
    elif field == "photo":
        await state.set_state(EditProfile.photo)
        await callback.message.answer(
            _prompt("Фото", t.EDIT_PHOTO),
            parse_mode="HTML",
            reply_markup=keep_kb(),
        )
    elif field == "height":
        await state.set_state(EditProfile.height)
        current = f"{profile.height} см" if profile.height else "не указан"
        await callback.message.answer(
            _prompt("Рост", t.EDIT_HEIGHT, current),
            parse_mode="HTML",
            reply_markup=height_edit_kb(),
        )
    elif field == "gender":
        await state.set_state(EditProfile.gender)
        await callback.message.answer(
            f"<b>{t.ASK_GENDER_TITLE}</b>\n{html.escape(t.ASK_GENDER_BODY)}",
            parse_mode="HTML",
            reply_markup=gender_inline(),
        )
    elif field == "dance":
        await state.set_state(EditProfile.dance)
        await callback.message.answer(
            f"<b>{t.ASK_DANCE_TITLE}</b>\n{html.escape(t.ASK_DANCE_BODY)}",
            parse_mode="HTML",
            reply_markup=dance_inline(),
        )
    elif field == "faculty":
        await state.set_state(EditProfile.edu_level)
        sent = await callback.message.answer(
            f"<b>{t.ASK_LEVEL_TITLE}</b>\n{html.escape(t.ASK_LEVEL_BODY)}\n\n"
            f"{t.BTN_BACK} — не менять группу.",
            parse_mode="HTML",
            reply_markup=level_inline(),
        )
        await state.update_data(wizard_chat_id=sent.chat.id, wizard_message_id=sent.message_id)
    else:
        await callback.answer(t.STALE_BUTTON, show_alert=True)
        return
    await callback.answer()


async def _done(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, user_id: int
) -> None:
    await _refresh_card(bot, state, session, user_id)
    await state.clear()
    try:
        await message.edit_text(t.EDIT_DONE, reply_markup=None)
    except Exception:
        await message.answer(t.EDIT_DONE)


@router.callback_query(F.data == "edit:height:clear")
async def clear_height(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if await state.get_state() != EditProfile.height.state:
        await callback.answer(t.STALE_BUTTON, show_alert=True)
        return
    profile = await _profile_for_edit(session, callback.from_user.id)
    if not profile or callback.message is None:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    await ProfileRepo(session).update_fields(profile, height=None)
    await _done(callback.message, state, session, bot, callback.from_user.id)
    await callback.answer(t.EDIT_DONE)


@router.callback_query(F.data.startswith("set:gender:"))
async def set_gender(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if await state.get_state() != EditProfile.gender.state or callback.message is None:
        await callback.answer(t.STALE_BUTTON, show_alert=True)
        return
    gender = (callback.data or "").rsplit(":", 1)[-1]
    if gender not in {"male", "female"}:
        await callback.answer()
        return
    profile = await _profile_for_edit(session, callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    await ProfileRepo(session).update_fields(
        profile, gender=gender, looking_for=opposite_gender(gender)
    )
    await _done(callback.message, state, session, bot, callback.from_user.id)
    await callback.answer(t.EDIT_DONE)


@router.callback_query(F.data.startswith("set:dance:"))
async def set_dance(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if await state.get_state() != EditProfile.dance.state or callback.message is None:
        await callback.answer(t.STALE_BUTTON, show_alert=True)
        return
    dance = (callback.data or "").rsplit(":", 1)[-1]
    if dance not in {"none", "some", "confident"}:
        await callback.answer()
        return
    profile = await _profile_for_edit(session, callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return
    await ProfileRepo(session).update_fields(profile, dance_experience=dance)
    await _done(callback.message, state, session, bot, callback.from_user.id)
    await callback.answer(t.EDIT_DONE)


async def _wizard(bot: Bot, state: FSMContext, text: str, markup) -> None:
    data = await state.get_data()
    chat_id = data.get("wizard_chat_id")
    message_id = data.get("wizard_message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="HTML",
            reply_markup=markup,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("edu:"))
async def edit_edu(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    current = await state.get_state() or ""
    if not current.startswith("EditProfile"):
        await callback.answer(t.STALE_BUTTON, show_alert=True)
        return
    data_cb = callback.data or ""
    profile = await _profile_for_edit(session, callback.from_user.id)
    if not profile:
        await callback.answer(t.NO_PROFILE, show_alert=True)
        return

    if data_cb == "edu:back":
        if current == EditProfile.edu_program.state:
            await state.set_state(EditProfile.edu_level)
            await _wizard(
                bot,
                state,
                f"<b>{t.ASK_LEVEL_TITLE}</b>\n{html.escape(t.ASK_LEVEL_BODY)}",
                level_inline(),
            )
        elif current == EditProfile.edu_course.state:
            await state.set_state(EditProfile.edu_program)
            await _wizard(
                bot,
                state,
                f"<b>{t.ASK_PROGRAM_TITLE}</b>\n{html.escape(t.ASK_PROGRAM_BODY)}",
                programs_inline(),
            )
        elif current == EditProfile.edu_group.state:
            await state.set_state(EditProfile.edu_course)
            await _wizard(
                bot,
                state,
                f"<b>{t.ASK_COURSE_TITLE}</b>\n{html.escape(t.ASK_COURSE_BODY)}",
                course_inline(),
            )
        else:
            await _show_fields(bot, state)
            try:
                await callback.message.edit_text("Группу не менял.", reply_markup=None)
            except Exception:
                pass
        await callback.answer()
        return

    if data_cb == "edu:lvl:ma":
        await callback.answer(t.MASTER_SOON, show_alert=True)
        return
    if data_cb == "edu:lvl:ba":
        await state.update_data(edu_level=LEVEL_BACHELOR)
        await state.set_state(EditProfile.edu_program)
        await _wizard(
            bot,
            state,
            f"<b>{t.ASK_PROGRAM_TITLE}</b>\n{html.escape(t.ASK_PROGRAM_BODY)}",
            programs_inline(),
        )
        await callback.answer()
        return
    if data_cb.startswith("edu:prg:"):
        program = data_cb.split(":", 2)[2]
        if program not in BACHELOR_PROGRAMS:
            await callback.answer(t.STALE_BUTTON, show_alert=True)
            return
        await state.update_data(edu_program=program)
        await state.set_state(EditProfile.edu_course)
        await _wizard(
            bot,
            state,
            f"<b>{t.ASK_COURSE_TITLE}</b>\n{html.escape(t.ASK_COURSE_BODY)}",
            course_inline(),
        )
        await callback.answer()
        return
    if data_cb.startswith("edu:crs:"):
        raw = data_cb.rsplit(":", 1)[-1]
        if raw not in {"1", "2", "3", "4"}:
            await callback.answer()
            return
        await state.update_data(edu_course=int(raw))
        await state.set_state(EditProfile.edu_group)
        data = await state.get_data()
        await _wizard(
            bot,
            state,
            f"<b>{t.ASK_GROUP_TITLE}</b>\n{html.escape(t.ASK_GROUP_BODY)}",
            group_inline(data["edu_program"], int(raw)),
        )
        await callback.answer()
        return
    if data_cb.startswith("edu:grp:"):
        raw = data_cb.rsplit(":", 1)[-1]
        if raw not in {"1", "2", "3", "4"}:
            await callback.answer()
            return
        data = await state.get_data()
        program = data.get("edu_program")
        course = data.get("edu_course")
        if not program or not course:
            await callback.answer(t.STALE_BUTTON, show_alert=True)
            return
        faculty = format_group(program, int(course), int(raw))
        await ProfileRepo(session).update_fields(profile, faculty=faculty)
        await _refresh_card(bot, state, session, callback.from_user.id)
        await state.clear()
        try:
            await callback.message.edit_text(
                f"{t.EDIT_DONE} Группа: {html.escape(faculty)}",
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception:
            pass
        await callback.answer(t.EDIT_DONE)
        return
    await callback.answer()


@router.message(EditProfile.name, F.text)
async def edit_name(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    name = (message.text or "").strip()
    if name in {t.BTN_BACK, t.EDIT_KEEP}:
        await _show_fields(bot, state)
        await message.answer("Не менял.")
        return
    if name in t.RESERVED_INPUTS:
        await message.answer(t.NAME_IS_BUTTON)
        return
    if not name or len(name) > 50:
        await message.answer(t.NAME_TOO_LONG if len(name) > 50 else t.NAME_EMPTY)
        return
    profile = await _profile_for_edit(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, name=name)
    await _refresh_card(bot, state, session, message.from_user.id)
    await state.clear()
    await message.answer(t.EDIT_DONE)


@router.message(EditProfile.about, F.text)
async def edit_about(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    about = (message.text or "").strip()
    if about in {t.BTN_BACK, t.EDIT_KEEP}:
        await _show_fields(bot, state)
        await message.answer("Не менял.")
        return
    if len(about) < 5:
        await message.answer(t.ABOUT_TOO_SHORT)
        return
    if len(about) > 400:
        await message.answer(t.ABOUT_TOO_LONG)
        return
    profile = await _profile_for_edit(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, about=about)
    await _refresh_card(bot, state, session, message.from_user.id)
    await state.clear()
    await message.answer(t.EDIT_DONE)


@router.message(EditProfile.height, F.text)
async def edit_height(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    raw = (message.text or "").strip()
    if raw in {t.BTN_BACK, t.EDIT_KEEP}:
        await _show_fields(bot, state)
        await message.answer("Не менял.")
        return
    if raw in {t.EDIT_CLEAR_HEIGHT, t.SKIP}:
        height = None
    else:
        height = parse_height(raw)
        if height is None:
            await message.answer(t.INVALID_HEIGHT, reply_markup=height_edit_kb())
            return
    profile = await _profile_for_edit(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, height=height)
    await _refresh_card(bot, state, session, message.from_user.id)
    await state.clear()
    await message.answer(t.EDIT_DONE)


@router.message(EditProfile.photo, F.photo)
async def edit_photo(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    profile = await _profile_for_edit(session, message.from_user.id)
    if not profile:
        await message.answer(t.NO_PROFILE)
        return
    await ProfileRepo(session).update_fields(profile, photo_file_id=message.photo[-1].file_id)
    await _refresh_card(bot, state, session, message.from_user.id)
    await state.clear()
    await message.answer(t.EDIT_DONE)


@router.message(EditProfile.photo)
async def edit_photo_bad(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.text in {t.BTN_BACK, t.EDIT_KEEP}:
        await _show_fields(bot, state)
        await message.answer("Не менял.")
        return
    await message.answer(t.NEED_PHOTO, reply_markup=keep_kb())


@router.message(StateFilter(EditProfile))
async def edit_unexpected(message: Message) -> None:
    await message.answer("Нужна кнопка под сообщением или текст, который просили. /cancel — в меню.")
