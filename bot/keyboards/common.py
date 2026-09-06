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
        [KeyboardButton(text=t.BTN_MY_PROFILE), KeyboardButton(text=t.BTN_LIKES_ME)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=t.BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def menu_for(user_id: int | None, config: Config | None) -> ReplyKeyboardMarkup:
    return main_menu_kb(is_admin=is_admin(user_id, config))


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t.BTN_ADMIN_STATS),
                KeyboardButton(text=t.BTN_ADMIN_USERS),
            ],
            [
                KeyboardButton(text=t.BTN_ADMIN_USER),
                KeyboardButton(text=t.BTN_ADMIN_BROADCAST),
            ],
            [
                KeyboardButton(text=t.BTN_ADMIN_BAN),
                KeyboardButton(text=t.BTN_ADMIN_UNBAN),
            ],
            [KeyboardButton(text=t.BTN_ADMIN_BACK)],
        ],
        resize_keyboard=True,
    )


def admin_pick_kb() -> ReplyKeyboardMarkup:
    """Выбор пользователя: список + назад в админку."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_ADMIN_PICK_LIST)],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )


def admin_back_kb() -> ReplyKeyboardMarkup:
    """Только «Назад» — возврат в админку (рассылка и т.п.)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.CANCEL)]],
        resize_keyboard=True,
    )


def with_main_menu(
    base: ReplyKeyboardMarkup, *, is_admin: bool = False
) -> ReplyKeyboardMarkup:
    """Поля редактирования + нижнее меню, чтобы оно оставалось рабочим."""
    rows = [list(row) for row in base.keyboard]
    rows.append([KeyboardButton(text=t.BTN_BROWSE)])
    rows.append(
        [
            KeyboardButton(text=t.BTN_MY_PROFILE),
            KeyboardButton(text=t.BTN_LIKES_ME),
        ]
    )
    if is_admin:
        rows.append([KeyboardButton(text=t.BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.GENDER_MALE), KeyboardButton(text=t.GENDER_FEMALE)],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )


def dance_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.DANCE_NONE), KeyboardButton(text=t.DANCE_SOME)],
            [KeyboardButton(text=t.DANCE_CONFIDENT)],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )


def skip_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.SKIP)],
            [KeyboardButton(text=t.CANCEL)],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.CANCEL)]],
        resize_keyboard=True,
    )


def without_cancel(base: ReplyKeyboardMarkup) -> ReplyKeyboardMarkup:
    """Reply-клавиатура без ряда «Назад» (для редактирования)."""
    rows = [
        list(row)
        for row in base.keyboard
        if not (len(row) == 1 and row[0].text == t.CANCEL)
    ]
    return ReplyKeyboardMarkup(keyboard=rows or [[KeyboardButton(text=t.SKIP)]], resize_keyboard=True)


def edit_back_ikb() -> InlineKeyboardMarkup:
    """«Назад» у сообщения — к списку полей."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.CANCEL, callback_data="edit:back")],
        ]
    )


def edit_gender_ikb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t.GENDER_MALE, callback_data="editset:gender:male"
                ),
                InlineKeyboardButton(
                    text=t.GENDER_FEMALE, callback_data="editset:gender:female"
                ),
            ],
            [InlineKeyboardButton(text=t.CANCEL, callback_data="edit:back")],
        ]
    )


def edit_dance_ikb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t.DANCE_NONE, callback_data="editset:dance:none"
                ),
                InlineKeyboardButton(
                    text=t.DANCE_SOME, callback_data="editset:dance:some"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t.DANCE_CONFIDENT, callback_data="editset:dance:confident"
                ),
            ],
            [InlineKeyboardButton(text=t.CANCEL, callback_data="edit:back")],
        ]
    )


def edit_height_ikb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.SKIP, callback_data="editset:height:skip")],
            [InlineKeyboardButton(text=t.CANCEL, callback_data="edit:back")],
        ]
    )


def yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.YES), KeyboardButton(text=t.NO)],
        ],
        resize_keyboard=True,
    )


def feed_kb(profile_id: int, *, index: int, total: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t.BTN_PREV, callback_data=f"feed:prev:{profile_id}"
                ),
                InlineKeyboardButton(
                    text=f"{index + 1}/{total}", callback_data="feed:noop"
                ),
                InlineKeyboardButton(
                    text=t.BTN_NEXT, callback_data=f"feed:next:{profile_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t.BTN_LIKE, callback_data=f"feed:like:{profile_id}"
                ),
            ],
            [InlineKeyboardButton(text=t.BTN_SLEEP, callback_data="feed:sleep")],
        ]
    )


def likes_kb(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_LIKE, callback_data=f"likes:like:{target_id}"),
                InlineKeyboardButton(text=t.BTN_DISLIKE, callback_data=f"likes:skip:{target_id}"),
            ],
            [InlineKeyboardButton(text=t.BACK_TO_MENU, callback_data="likes:menu")],
        ]
    )


def match_kb(username: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if username:
        rows.append(
            [InlineKeyboardButton(text=t.BTN_WRITE, url=f"https://t.me/{username}")]
        )
    rows.append([InlineKeyboardButton(text=t.BTN_MATCH_OK, callback_data="match:ok")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_profile_kb(is_paused: bool) -> InlineKeyboardMarkup:
    pause_text = t.BTN_UNPAUSE if is_paused else t.BTN_PAUSE
    pause_data = "profile:unpause" if is_paused else "profile:pause"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_EDIT, callback_data="profile:edit")],
            [InlineKeyboardButton(text=t.BTN_REFILL, callback_data="profile:refill")],
            [InlineKeyboardButton(text=pause_text, callback_data=pause_data)],
            [InlineKeyboardButton(text=t.BTN_DELETE, callback_data="profile:delete")],
            [InlineKeyboardButton(text=t.BACK_TO_MENU, callback_data="profile:menu")],
        ]
    )


def edit_fields_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_EDIT_NAME, callback_data="edit:name"),
                InlineKeyboardButton(text=t.BTN_EDIT_PHOTO, callback_data="edit:photo"),
            ],
            [
                InlineKeyboardButton(text=t.BTN_EDIT_GENDER, callback_data="edit:gender"),
                InlineKeyboardButton(text=t.BTN_EDIT_FACULTY, callback_data="edit:faculty"),
            ],
            [
                InlineKeyboardButton(text=t.BTN_EDIT_HEIGHT, callback_data="edit:height"),
                InlineKeyboardButton(text=t.BTN_EDIT_DANCE, callback_data="edit:dance"),
            ],
            [InlineKeyboardButton(text=t.BTN_EDIT_ABOUT, callback_data="edit:about")],
            [InlineKeyboardButton(text=t.BACK_TO_MENU, callback_data="profile:menu")],
        ]
    )
