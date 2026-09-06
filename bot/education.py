"""Выбор уровня / направления / курса / группы."""

from __future__ import annotations

from datetime import date

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot import texts as t

LEVEL_BACHELOR = "Бакалавриат"
LEVEL_MASTER = "Магистратура"

BACHELOR_PROGRAMS = ("И", "ИЯ", "МБ", "МКИ", "МПБЭ", "РИС", "Ю")

SUBGROUPS = (1, 2, 3, 4)


def intake_year_short(course: int, *, today: date | None = None) -> int:
    """Короткий год поступления для курса (1→текущий набор, 2→прошлый, …)."""
    today = today or date.today()
    # Учебный год стартует в августе
    start_year = today.year if today.month >= 8 else today.year - 1
    return (start_year % 100) - (course - 1)


def format_group(program: str, course: int, subgroup: int) -> str:
    year = intake_year_short(course)
    return f"{program}-{year}-{subgroup}"


def level_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=LEVEL_BACHELOR), KeyboardButton(text=LEVEL_MASTER)],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )


def bachelor_programs_kb() -> ReplyKeyboardMarkup:
    row1 = [KeyboardButton(text=p) for p in BACHELOR_PROGRAMS[:3]]
    row2 = [KeyboardButton(text=p) for p in BACHELOR_PROGRAMS[3:6]]
    row3 = [KeyboardButton(text=BACHELOR_PROGRAMS[6])]
    return ReplyKeyboardMarkup(
        keyboard=[row1, row2, row3, [KeyboardButton(text=t.CANCEL)]],
        resize_keyboard=True,
    )


def course_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1"),
                KeyboardButton(text="2"),
                KeyboardButton(text="3"),
                KeyboardButton(text="4"),
            ],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )


def group_kb(program: str, course: int) -> ReplyKeyboardMarkup:
    labels = [format_group(program, course, s) for s in SUBGROUPS]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0]), KeyboardButton(text=labels[1])],
            [KeyboardButton(text=labels[2]), KeyboardButton(text=labels[3])],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )
