"""Кнопки под старыми сообщениями снимаются, когда человек жмёт новую."""

from __future__ import annotations

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message

from bot import texts as t
from bot.education import LEVEL_BACHELOR, LEVEL_MASTER

_live: dict[int, list[int]] = {}


def _buttons() -> frozenset[str]:
    return t.RESERVED_INPUTS | {LEVEL_BACHELOR, LEVEL_MASTER}


async def discard(bot: Bot, chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def clear_live(bot: Bot, chat_id: int, *, keep: int | None = None) -> None:
    kept: list[int] = []
    for message_id in _live.get(chat_id, []):
        if keep is not None and message_id == keep:
            kept.append(message_id)
            continue
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=None
            )
        except Exception:
            pass
    if kept:
        _live[chat_id] = kept
    else:
        _live.pop(chat_id, None)


async def arm(bot: Bot, chat_id: int, message_id: int) -> None:
    """Оставить кнопки только на этом сообщении."""
    await clear_live(bot, chat_id, keep=message_id)
    ids = [item for item in _live.get(chat_id, []) if item != message_id]
    ids.append(message_id)
    _live[chat_id] = ids[-40:]


async def answer_inline(message: Message, text: str, markup, **kwargs) -> Message:
    sent = await message.answer(text, reply_markup=markup, **kwargs)
    if markup is not None:
        await arm(message.bot, sent.chat.id, sent.message_id)
    return sent


class ClearButtonsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot: Bot = data["bot"]
        if isinstance(event, Message) and (event.text or "") in _buttons():
            await clear_live(bot, event.chat.id)
        elif isinstance(event, CallbackQuery) and event.message:
            await clear_live(
                bot, event.message.chat.id, keep=event.message.message_id
            )
        return await handler(event, data)
