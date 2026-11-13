"""Выбор уровня / направления / курса / группы."""

from __future__ import annotations

from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

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


def _nav(*, back: bool = True) -> list[KeyboardButton]:
    if back:
        return [KeyboardButton(text=t.BTN_BACK), KeyboardButton(text=t.BTN_CANCEL)]
    return [KeyboardButton(text=t.BTN_CANCEL)]


def _back_inline() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=t.BTN_BACK, callback_data="edu:back")]


def level_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=LEVEL_BACHELOR), KeyboardButton(text=LEVEL_MASTER)],
            _nav(),
        ],
        resize_keyboard=True,
    )


def level_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=LEVEL_BACHELOR, callback_data="edu:lvl:ba"),
                InlineKeyboardButton(text=LEVEL_MASTER, callback_data="edu:lvl:ma"),
            ],
            _back_inline(),
        ]
    )


def bachelor_programs_kb() -> ReplyKeyboardMarkup:
    row1 = [KeyboardButton(text=p) for p in BACHELOR_PROGRAMS[:3]]
    row2 = [KeyboardButton(text=p) for p in BACHELOR_PROGRAMS[3:6]]
    row3 = [KeyboardButton(text=BACHELOR_PROGRAMS[6])]
    return ReplyKeyboardMarkup(
        keyboard=[row1, row2, row3, _nav()],
        resize_keyboard=True,
    )


def programs_inline() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=p, callback_data=f"edu:prg:{p}") for p in BACHELOR_PROGRAMS
    ]
    rows: list[list[InlineKeyboardButton]] = [buttons[:3], buttons[3:6], buttons[6:]]
    rows.append(_back_inline())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def course_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1"),
                KeyboardButton(text="2"),
                KeyboardButton(text="3"),
                KeyboardButton(text="4"),
            ],
            _nav(),
        ],
        resize_keyboard=True,
    )


def course_inline() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=str(i), callback_data=f"edu:crs:{i}") for i in range(1, 5)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row, _back_inline()])


def group_inline(program: str, course: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=format_group(program, course, subgroup),
            callback_data=f"edu:grp:{subgroup}",
        )
        for subgroup in SUBGROUPS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[:2], buttons[2:], _back_inline()]
    )


def group_kb(program: str, course: int) -> ReplyKeyboardMarkup:
    labels = [format_group(program, course, s) for s in SUBGROUPS]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0]), KeyboardButton(text=labels[1])],
            [KeyboardButton(text=labels[2]), KeyboardButton(text=labels[3])],
            _nav(),
        ],
        resize_keyboard=True,
    )
