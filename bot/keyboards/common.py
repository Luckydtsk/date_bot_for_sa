from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot import texts as t


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_BROWSE)],
            [KeyboardButton(text=t.BTN_MY_PROFILE), KeyboardButton(text=t.BTN_LIKES_ME)],
        ],
        resize_keyboard=True,
    )


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
            [InlineKeyboardButton(text=t.BTN_EDIT_GENDER, callback_data="edit:gender")],
            [
                InlineKeyboardButton(text=t.BTN_EDIT_FACULTY, callback_data="edit:faculty"),
                InlineKeyboardButton(text=t.BTN_EDIT_HEIGHT, callback_data="edit:height"),
            ],
            [InlineKeyboardButton(text=t.BTN_EDIT_DANCE, callback_data="edit:dance")],
            [
                InlineKeyboardButton(text=t.BTN_EDIT_ABOUT, callback_data="edit:about"),
                InlineKeyboardButton(text=t.BTN_EDIT_CONTACT, callback_data="edit:contact"),
            ],
            [InlineKeyboardButton(text=t.BACK_TO_MENU, callback_data="profile:menu")],
        ]
    )
