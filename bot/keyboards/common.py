from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot import texts as t
from bot.config import Config


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def is_admin(user_id: int | None, config: Config | None) -> bool:
    return bool(config and user_id and user_id in config.admin_ids)


def main_menu_kb(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=t.BTN_BROWSE)],
        [KeyboardButton(text=t.BTN_LIKES_ME), KeyboardButton(text=t.BTN_MATCHES)],
        [KeyboardButton(text=t.BTN_MY_PROFILE), KeyboardButton(text=t.BTN_HELP)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=t.BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def menu_for(user_id: int | None, config: Config | None) -> ReplyKeyboardMarkup:
    return main_menu_kb(is_admin=is_admin(user_id, config))


def _nav_row(*, back: bool) -> list[KeyboardButton]:
    if back:
        return [KeyboardButton(text=t.BTN_BACK), KeyboardButton(text=t.BTN_CANCEL)]
    return [KeyboardButton(text=t.BTN_CANCEL)]


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[_nav_row(back=False)], resize_keyboard=True)


def back_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[_nav_row(back=True)], resize_keyboard=True)


def skip_back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.SKIP)], _nav_row(back=True)],
        resize_keyboard=True,
    )


def gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.GENDER_MALE), KeyboardButton(text=t.GENDER_FEMALE)],
            _nav_row(back=True),
        ],
        resize_keyboard=True,
    )


def dance_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.DANCE_NONE), KeyboardButton(text=t.DANCE_SOME)],
            [KeyboardButton(text=t.DANCE_CONFIDENT)],
            _nav_row(back=True),
        ],
        resize_keyboard=True,
    )


def feed_controls_kb() -> ReplyKeyboardMarkup:
    """Листание вместо меню, пока человек в анкетах."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_BACK), KeyboardButton(text=t.FEED_NEXT)],
            [KeyboardButton(text=t.BTN_LIKE), KeyboardButton(text=t.BTN_NOPE)],
            [
                KeyboardButton(text=t.FEED_ALL),
                KeyboardButton(text=t.FEED_LIKED),
                KeyboardButton(text=t.FEED_DISLIKED),
            ],
            [KeyboardButton(text=t.BTN_ADMIN_BACK)],
        ],
        resize_keyboard=True,
    )


def likes_kb(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_LIKE, callback_data=f"in:y:{profile_id}"),
                InlineKeyboardButton(text=t.BTN_NOPE, callback_data=f"in:x:{profile_id}"),
            ],
            [InlineKeyboardButton(text=t.BTN_CLOSE, callback_data="in:c")],
        ]
    )


def match_kb(username: str | None) -> InlineKeyboardMarkup | None:
    if not username:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_WRITE, url=f"https://t.me/{username}")]
        ]
    )


def pairs_kb(partners: list[tuple[str, str]]) -> InlineKeyboardMarkup | None:
    """partners: (label, username) только для тех, у кого есть @username."""
    if not partners:
        return None
    rows = [
        [InlineKeyboardButton(text=label[:64], url=f"https://t.me/{username}")]
        for label, username in partners[:30]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_profile_kb(*, paused: bool) -> InlineKeyboardMarkup:
    pause = "Показывать снова" if paused else "Скрыть из ленты"
    pause_data = "profile:unpause" if paused else "profile:pause"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить", callback_data="profile:edit")],
            [InlineKeyboardButton(text=pause, callback_data=pause_data)],
            [InlineKeyboardButton(text="Заполнить заново", callback_data="profile:refill")],
            [InlineKeyboardButton(text="Удалить анкету", callback_data="profile:delete")],
        ]
    )


def edit_fields_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Имя", callback_data="edit:name"),
                InlineKeyboardButton(text="Фото", callback_data="edit:photo"),
            ],
            [
                InlineKeyboardButton(text="Пол", callback_data="edit:gender"),
                InlineKeyboardButton(text="Учёба", callback_data="edit:faculty"),
            ],
            [
                InlineKeyboardButton(text="Рост", callback_data="edit:height"),
                InlineKeyboardButton(text="Танцы", callback_data="edit:dance"),
            ],
            [InlineKeyboardButton(text="О себе", callback_data="edit:about")],
            [InlineKeyboardButton(text="← К анкете", callback_data="edit:back")],
        ]
    )


def keep_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.EDIT_KEEP, callback_data="edit:back")]
        ]
    )


def height_edit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.EDIT_CLEAR_HEIGHT, callback_data="edit:height:clear")],
            [InlineKeyboardButton(text=t.EDIT_KEEP, callback_data="edit:back")],
        ]
    )


def gender_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.GENDER_MALE, callback_data="set:gender:male"),
                InlineKeyboardButton(text=t.GENDER_FEMALE, callback_data="set:gender:female"),
            ],
            [InlineKeyboardButton(text=t.EDIT_KEEP, callback_data="edit:back")],
        ]
    )


def dance_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.DANCE_NONE, callback_data="set:dance:none"),
                InlineKeyboardButton(text=t.DANCE_SOME, callback_data="set:dance:some"),
            ],
            [
                InlineKeyboardButton(
                    text=t.DANCE_CONFIDENT, callback_data="set:dance:confident"
                )
            ],
            [InlineKeyboardButton(text=t.EDIT_KEEP, callback_data="edit:back")],
        ]
    )


def confirm_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, уверен", callback_data=f"ask:{kind}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"ask:{kind}:no"),
            ]
        ]
    )


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_ADMIN_STATS, callback_data="admin:stats"),
                InlineKeyboardButton(text=t.BTN_ADMIN_USERS, callback_data="admin:users"),
            ],
            [
                InlineKeyboardButton(text=t.BTN_ADMIN_USER, callback_data="admin:ask:view"),
                InlineKeyboardButton(text=t.BTN_ADMIN_BROADCAST, callback_data="admin:ask:broadcast"),
            ],
            [
                InlineKeyboardButton(text=t.BTN_ADMIN_BAN, callback_data="admin:ask:ban"),
                InlineKeyboardButton(text=t.BTN_ADMIN_UNBAN, callback_data="admin:ask:unban"),
            ],
        ]
    )


def admin_pick_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_ADMIN_PICK_LIST, callback_data="admin:openlist")],
            [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="admin:cancel")],
        ]
    )
