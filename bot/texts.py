"""Тексты бота. Короткие, с одинаковыми названиями кнопок."""

from __future__ import annotations

import html

BALL_NAME = "студенческий бал"

# --- Кнопки меню (они же слова в текстах, чтобы не расходились) ---
BTN_BROWSE = "👀 Анкеты"
BTN_LIKES_ME = "💘 Кому я нравлюсь"
BTN_MATCHES = "💞 Мои пары"
BTN_MY_PROFILE = "📝 Моя анкета"
BTN_HELP = "❓ Помощь"
BTN_ADMIN = "🛠 Админка"

# Старая клавиатура могла остаться в чате до первого /start.
ALIAS_BROWSE = "👀 Смотреть анкеты"

BTN_BACK = "← Назад"
BTN_CANCEL = "Отмена"
SKIP = "Пропустить"
YES = "Да"
NO = "Нет"

GENDER_MALE = "Парень"
GENDER_FEMALE = "Девушка"
DANCE_NONE = "Нет опыта"
DANCE_SOME = "Немного"
DANCE_CONFIDENT = "Уверенно"

BTN_LIKE = "❤️ Нравится"
BTN_NOPE = "👎 Не моё"
BTN_WRITE = "✉️ Написать"
BTN_CLOSE = "Закрыть"
FEED_NEXT = "Дальше →"
FEED_ALL = "Все"
FEED_LIKED = "Мои ❤️"
FEED_DISLIKED = "Мои 👎"
FEED_MARK = "✓ "

BTN_ADMIN_STATS = "📊 Статистика"
BTN_ADMIN_USERS = "👥 Список анкет"
BTN_ADMIN_USER = "🔍 Открыть анкету"
BTN_ADMIN_BROADCAST = "📢 Рассылка"
BTN_ADMIN_BAN = "🚫 Бан"
BTN_ADMIN_UNBAN = "✅ Разбан"
BTN_ADMIN_BACK = "В меню"
BTN_ADMIN_PICK_LIST = "📋 Выбрать из списка"

MENU_BUTTONS = frozenset(
    {
        BTN_BROWSE,
        ALIAS_BROWSE,
        BTN_LIKES_ME,
        BTN_MATCHES,
        BTN_MY_PROFILE,
        BTN_HELP,
        BTN_ADMIN,
        BTN_ADMIN_STATS,
        BTN_ADMIN_USERS,
        BTN_ADMIN_USER,
        BTN_ADMIN_BROADCAST,
        BTN_ADMIN_BAN,
        BTN_ADMIN_UNBAN,
        BTN_ADMIN_BACK,
        BTN_ADMIN_PICK_LIST,
    }
)

RESERVED_INPUTS = MENU_BUTTONS | {
    BTN_BACK,
    BTN_CANCEL,
    SKIP,
    YES,
    NO,
    GENDER_MALE,
    GENDER_FEMALE,
    DANCE_NONE,
    DANCE_SOME,
    DANCE_CONFIDENT,
    FEED_NEXT,
    FEED_ALL,
    FEED_LIKED,
    FEED_DISLIKED,
    FEED_MARK + FEED_ALL,
    FEED_MARK + FEED_LIKED,
    FEED_MARK + FEED_DISLIKED,
    BTN_LIKE,
    BTN_NOPE,
}


def step(n: int, total: int, title: str, body: str, *, back: bool) -> str:
    tail = f"{BTN_CANCEL} — выйти."
    if back:
        tail = f"{BTN_BACK} — назад. " + tail
    return (
        f"<b>Шаг {n} из {total}</b> · {html.escape(title)}\n"
        f"{html.escape(body)}\n"
        f"{html.escape(tail)}"
    )


HELP_FULL = (
    "<b>Как пользоваться</b>\n"
    "Парни видят девушек, девушки — парней.\n\n"
    f"{BTN_BROWSE} — анкеты по кругу. Внизу: назад, дальше, ❤️ или 👎. Решение можно поменять.\n"
    f"{BTN_LIKES_ME} — кто лайкнул тебя\n"
    f"{BTN_MATCHES} — взаимные, там «Написать»\n"
    f"{BTN_MY_PROFILE} — поправить или скрыть\n"
    f"{BTN_HELP} — этот текст\n\n"
    f"{BTN_BACK} — предыдущий вопрос. {BTN_CANCEL} — выйти.\n"
    "Меню внизу появится после анкеты."
)

REG_INTRO = "Дальше анкета. Внизу можно выйти, со следующего шага — вернуться назад."

CONTINUE_HIDDEN = (
    "Продолжим анкету. Пока не закончишь, старая скрыта.\n"
    f"{BTN_CANCEL} — выйти."
)

WELCOME_BACK_TAIL = f"Кнопки внизу. {BTN_HELP} — если забыл, что они делают."


def welcome_back(name: str) -> str:
    safe = html.escape(name.strip() or "привет")
    return f"С возвращением, <b>{safe}</b>.\n\n{WELCOME_BACK_TAIL}"


REG_DONE = (
    "<b>Анкета готова.</b>\n"
    f"{BTN_BROWSE} — смотреть людей и ставить ❤️ или 👎. Решение можно менять."
)

USERNAME_HINT = (
    "Нет @username — в «Мои пары» кнопка «Написать» может не появиться.\n"
    "Его включают в настройках Telegram: Имя пользователя."
)

REG_CANCELLED = f"Анкета не сохранилась. Заполнить снова — кнопка «Старт» в этом чате. {BTN_HELP} — как устроен бот."
REFILL_CANCELLED = "Остановились. Старая анкета скрыта, пока не закончишь новую. Нажми «Старт», чтобы продолжить."
EDIT_CANCELLED = "Правку отменил."
ADMIN_STEP_CANCELLED = "Админ-шаг отменён."
ALREADY_IDLE = f"Ты в меню. {BTN_HELP} — короткая шпаргалка."

FINISH_FIRST = (
    f"Сначала закончи анкету. {BTN_BACK} — назад, {BTN_CANCEL} — выйти."
)

HELP_WHILE_REG = f"\n\nАнкета ещё не сохранена. {BTN_BACK} — назад, {BTN_CANCEL} — выйти."
HELP_WHILE_REFILL = "\n\nНовая анкета не закончена, старая пока скрыта."

# --- Регистрация ---
ASK_NAME_TITLE = "Как к тебе обращаться?"
ASK_NAME_BODY = "Как на балу. До 50 символов."
ASK_GENDER_TITLE = "Ты парень или девушка?"
ASK_GENDER_BODY = "Парни видят девушек, девушки — парней."
ASK_LEVEL_TITLE = "Где учишься?"
ASK_LEVEL_BODY = "Бакалавриат или магистратура."
ASK_FACULTY_TITLE = "Направление, курс и группа"
ASK_FACULTY_BODY = "Напиши всё одним сообщением."
ASK_HEIGHT_TITLE = "Рост"
ASK_HEIGHT_BODY = "Число от 100 до 250 или «Пропустить»."
ASK_DANCE_TITLE = "Опыт танцев"
ASK_DANCE_BODY = "Как есть."
ASK_ABOUT_TITLE = "О себе"
ASK_ABOUT_BODY = "Пара фраз: танцы, кого ищешь. От 5 до 400 символов."
ASK_PHOTO_TITLE = "Фото"
ASK_PHOTO_BODY = "Одно фото, где видно лицо. Не файл."
ASK_CONTACT_TITLE = "Как с тобой связаться?"
ASK_CONTACT_BODY = "Нет @username. Напиши @ник, телефон или «в личке». Можно пропустить."
MASTER_SOON = "Магистратуры пока нет. Выбери бакалавриат."

NAME_TOO_LONG = "Слишком длинное имя. Максимум 50 символов."
NAME_EMPTY = "Напиши имя текстом."
NAME_IS_BUTTON = "Это подпись кнопки, а не имя. Напиши, как к тебе обращаться."
ABOUT_TOO_LONG = "О себе — максимум 400 символов. Сократи чуть-чуть."
ABOUT_TOO_SHORT = "Хотя бы пару слов, от 5 символов."
NEED_PHOTO = "Нужно именно фото. Пришли картинку как фото, не как документ."
NEED_TEXT = "Напиши текстом или нажми кнопку внизу."
INVALID_HEIGHT = "Рост — число от 100 до 250, либо «Пропустить»."
USE_BUTTONS = "Выбери вариант кнопкой. Клавиатура внизу."
CONTACT_TOO_LONG = "Контакт слишком длинный. До 200 символов, или «Пропустить»."
FACULTY_BAD = "Напиши направление, курс и группу текстом. До 100 символов."

# --- Карточка ---
DANCE_LABEL = {
    "none": "нет опыта",
    "some": "немного",
    "confident": "уверенно",
}


def format_card(profile) -> str:
    gender = GENDER_MALE if profile.gender == "male" else GENDER_FEMALE
    dance = DANCE_LABEL.get(profile.dance_experience, profile.dance_experience)
    lines = [
        f"<b>{html.escape(profile.name)}</b> · {html.escape(gender)}",
        f"Группа: {html.escape(profile.faculty)}",
        f"Танцы: {html.escape(str(dance))}",
    ]
    if profile.height:
        lines.insert(2, f"Рост: {int(profile.height)} см")
    lines.append("")
    lines.append(html.escape(profile.about))
    return "\n".join(lines)


MODE_LABEL = {
    "all": "все",
    "new": "новые",
    "liked": "мои ❤️",
    "nope": "мои 👎",
}

DECISION_NONE = "Решение: ещё не смотрел"
DECISION_LIKE = "Решение: ❤️ хочешь пойти вместе"
DECISION_NOPE = "Решение: 👎 не твоё"


def decision_match(profile) -> str:
    if profile.username:
        return "Решение: ✨ пара. Написать — в «Мои пары»."
    return f"Решение: ✨ пара. Нет @username, id {profile.telegram_id}"


def feed_caption(profile, *, index: int, total: int, mode: str, decision: str) -> str:
    label = MODE_LABEL.get(mode, mode)
    return f"{index} из {total} · {label}\n{decision}\n\n{format_card(profile)}"


def feed_intro(total: int, fresh: int, *, hidden: bool) -> str:
    text = (
        f"{total} анкет, без решения — {fresh}. "
        f"Листай внизу. {BTN_ADMIN_BACK} — к разделам."
    )
    if hidden:
        text += f"\nТвоя анкета скрыта. Включить — {BTN_MY_PROFILE}."
    return text


FEED_ONLY_ONE = "Тут одна анкета."
FEED_EMPTY_ALL = "Пока нет подходящих анкет. Они появятся, когда кто-то заполнит свою."
FEED_EMPTY_NEW = "Новых нет. «Все» — пересмотреть и поменять решение."
FEED_EMPTY_LIKED = "Пока никому не поставил ❤️."
FEED_EMPTY_NOPE = "Пока никому не поставил 👎."

FEED_FOOTER_EMPTY = "Фильтр можно сменить кнопками ниже."

TOAST_LIKE = "❤️ Сохранил. Если ответят взаимно — придёт пара."
TOAST_MATCH = "Пара. Написать — в «Мои пары»."
TOAST_NOPE = "👎 Сохранил. Вернуть ❤️ можно на этой же карточке."
TOAST_UNMATCH = "Пара снята. Вернуть можно кнопкой ❤️."
TOAST_SAME = "Так и стоит. Можно листать дальше."
TOAST_WRAP = "Дальше снова первая анкета — можно пересмотреть."
TOAST_GONE = "Этой анкеты больше нет в подборке."
TOAST_CLOSED = "Карточка закрыта. Меню внизу."

# --- Входящие и пары ---
LIKES_EMPTY = f"Пока никто не ждёт ответа. Смотри {BTN_MATCHES} и {BTN_BROWSE}."


def likes_intro(n: int) -> str:
    return f"Ждут ответ: {n}. ❤️ — пара, 👎 — убрать из списка."


def likes_caption(profile, *, index: int, total: int) -> str:
    return f"Ждёт ответ · {index} из {total}\n\n{format_card(profile)}"


MATCH_INTRO = "Это пара. Написать — кнопка в «Мои пары»."

MATCH_EMPTY = f"Пока нет взаимных ❤️. Ставь их в {BTN_BROWSE}."


def pairs_text(lines: list[str]) -> str:
    body = "\n".join(lines)
    return (
        f"<b>Твои пары — {len(lines)}</b>\n\n"
        f"{body}\n\n"
        f"Фото ещё раз — в {BTN_BROWSE}, фильтр «Мои ❤️»."
    )


SOMEONE_LIKED_YOU = f"Тебя лайкнули. Открой {BTN_LIKES_ME}."


def unmatched_notice(name: str) -> str:
    safe = html.escape(name.strip() or "Человек")
    return f"{safe} передумал. Пара снята, анкета остаётся в {BTN_BROWSE}."


# --- Своя анкета ---
def my_profile_caption(profile) -> str:
    status = "Скрыта из ленты." if not profile.is_active else "Видна другим."
    return f"<b>Твоя анкета</b>\n{status}\n\n{format_card(profile)}"


EDIT_WHICH = "Что поменять? Кнопки под фото."
EDIT_NAME = "Новое имя, до 50 символов."
EDIT_ABOUT = "Новый текст о себе, от 5 до 400 символов."
EDIT_HEIGHT = "Новый рост в сантиметрах, 100–250. Или «Не указывать»."
EDIT_PHOTO = "Пришли новое фото. Именно фото, не файл."
EDIT_DONE = "Обновили."
EDIT_KEEP = "Не менять"
EDIT_CLEAR_HEIGHT = "Не указывать"
CONFIRM_DELETE = "Удалить анкету? Лайки и пары тоже пропадут, вернуть нельзя."
CONFIRM_REFILL = "Заполнить заново? Пока заполняешь, старая скрыта. Лайки сбросятся в конце."
PROFILE_PAUSED = "Анкета скрыта. Смотреть других можно."
PROFILE_ACTIVE = "Анкета снова видна."
PROFILE_DELETED = "Анкета удалена. Нажми «Старт» в этом чате, чтобы создать новую."
NO_PROFILE = "Сначала анкета. Нажми «Старт» в этом чате."
PROFILE_BANNED = "Доступ закрыт. Если это ошибка — напиши организаторам бала."
CHOOSE_FIELD = "Что меняем?"

# --- Админка ---
ADMIN_ONLY = "Это только для организаторов."
ADMIN_PANEL_TITLE = "<b>Админка</b>\nВидишь только ты. «Отмена» — в обычное меню."
ADMIN_PICK_VIEW = "Чья анкета? id, @username или список."
ADMIN_PICK_BAN = "Кого скрыть? id, @username или список."
ADMIN_PICK_UNBAN = "Кого вернуть? id, @username или список."
ADMIN_BROADCAST_ASK = "Текст рассылки одним сообщением. Получат все с открытой анкетой. Отмена — не отправлять."
ADMIN_HELP = (
    "Команды:\n"
    "/stats — цифры\n"
    "/users — анкеты\n"
    "/user id или @ник\n"
    "/broadcast текст\n"
    "/ban id или @ник\n"
    "/unban id или @ник"
)
STATS_TEMPLATE = (
    "<b>Статистика</b>\n\n"
    "Анкет: {profiles}\n"
    "Активных: {active}\n"
    "Скрытых: {paused}\n"
    "Лайков: {likes}\n"
    "Пар: {matches}\n"
    "Заблокировано: {banned}"
)
BROADCAST_DONE = "Рассылка: {ok} дошло, {fail} ошибок, всего {total}."
BROADCAST_EMPTY = "Пустой текст не отправляю. Напиши сообщение или нажми Отмена."
BROADCAST_IS_BUTTON = "Это кнопка, не текст рассылки."
BAN_ADMIN_FORBIDDEN = "Организатора банить нельзя."
BAN_DONE = "Пользователь {tg_id} скрыт из бота."
UNBAN_DONE = "Пользователь {tg_id} снова может пользоваться ботом."
USER_NOT_FOUND = "В базе такой анкеты нет."
USERS_EMPTY = "Анкет пока нет."
USERS_BANNED_EMPTY = "Заблокированных нет."
USERS_BAN_EMPTY = "Некого банить."
USERS_PAGE = "Анкеты {start}–{end} из {total}. Нажми имя."
USER_LINE = "{n}. {name} · {gender} · {faculty}\nid {tg_id}{username}{flags}"

UNKNOWN = f"Не понял. Кнопки внизу. На шаге анкеты — {BTN_CANCEL}."
ERROR_TRY_AGAIN = "Не вышло. Попробуй ещё раз."
STALE_BUTTON = "Это старое сообщение. Открой раздел заново кнопкой внизу."
