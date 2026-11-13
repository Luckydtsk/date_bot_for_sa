"""Взаимные пары одним списком и кнопками «Написать»."""

import html

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts as t
from bot.config import Config
from bot.db.repositories import MatchRepo
from bot.keyboards.common import menu_for, pairs_kb
from bot.services import require_profile


async def open_pairs(message: Message, session: AsyncSession, config: Config) -> None:
    viewer = await require_profile(session, message.from_user.id)
    if not viewer:
        await message.answer(t.NO_PROFILE, reply_markup=menu_for(message.from_user.id, config))
        return
    partners = await MatchRepo(session).partners(viewer.id)
    menu = menu_for(message.from_user.id, config)
    if not partners:
        await message.answer(t.MATCH_EMPTY, reply_markup=menu)
        return

    lines: list[str] = []
    buttons: list[tuple[str, str]] = []
    for index, person in enumerate(partners, start=1):
        if person.username:
            contact = f"@{html.escape(person.username)}"
            buttons.append((f"{t.BTN_WRITE} {person.name}", person.username))
        elif person.contact:
            contact = html.escape(person.contact)
        else:
            contact = f"нет @username, id {person.telegram_id}"
        note = ""
        if person.is_banned or not person.is_active or not person.is_complete:
            note = " · анкета сейчас скрыта"
        lines.append(
            f"{index}. <b>{html.escape(person.name)}</b> · "
            f"{html.escape(person.faculty)} · {contact}{note}"
        )
    await message.answer(
        t.pairs_text(lines),
        parse_mode="HTML",
        reply_markup=menu,
    )
    keyboard = pairs_kb(buttons)
    if keyboard:
        await message.answer("Написать:", reply_markup=keyboard)
