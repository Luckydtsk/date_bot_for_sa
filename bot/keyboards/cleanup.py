"""Снятие inline-кнопок со старых сообщений, чтобы нельзя было жать повторно."""

from __future__ import annotations

from collections import defaultdict

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

_KB_MSGS = "kb_msgs"
_MAX_TRACKED = 30

# Сообщения с кнопками вне FSM (например, матч у другого пользователя)
_extra_kb: dict[int, list[int]] = defaultdict(list)


def remember_chat_keyboard(chat_id: int, message_id: int) -> None:
    ids = _extra_kb[chat_id]
    if message_id not in ids:
        ids.append(message_id)
    _extra_kb[chat_id] = ids[-_MAX_TRACKED:]


async def track_keyboard_message(state: FSMContext, message: Message | None) -> None:
    if message is None:
        return
    data = await state.get_data()
    ids: list[int] = list(data.get(_KB_MSGS, []))
    if message.message_id not in ids:
        ids.append(message.message_id)
    await state.update_data(**{_KB_MSGS: ids[-_MAX_TRACKED:]})
    remember_chat_keyboard(message.chat.id, message.message_id)


async def clear_tracked_keyboards(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    *,
    also: Message | None = None,
) -> None:
    """Убирает inline-клавиатуры со всех отслеживаемых сообщений (+ optionally текущее)."""
    data = await state.get_data()
    ids: set[int] = set(data.get(_KB_MSGS, []))
    ids.update(_extra_kb.pop(chat_id, []))
    if also is not None:
        ids.add(also.message_id)

    for message_id in ids:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
            )
        except Exception:
            pass

    await state.update_data(**{_KB_MSGS: []})


async def clear_message_keyboard(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
