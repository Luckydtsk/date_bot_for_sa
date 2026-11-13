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
}


def step(n: int, total: int, title: str, body: str, *, back: bool) -> str:
    tail = f"{BTN_CANCEL} или /cancel — выйти. Этот заход не сохранится."
    if back:
        tail = f"{BTN_BACK} — предыдущий шаг. " + tail
    return (
        f"<b>Шаг {n} из {total}</b>\n"
        f"{html.escape(title)}\n\n"
        f"{html.escape(body)}\n\n"
        f"{html.escape(tail)}"
    )


HELP_FULL = (
    "<b>Как пользоваться</b>\n\n"
    f"Бот, чтобы найти пару на {BALL_NAME}. "
    "Не лента знакомств: один вечер и человек, с которым хочется танцевать.\n\n"
    "<b>Кнопки внизу</b>\n\n"
    f"<b>{BTN_BROWSE}</b>\n"
    "Все, кто тебе подходит. Парни видят девушек, девушки — парней.\n"
    "Стрелки ← и → листают по кругу. Дошёл до конца — дальше снова первая. "
    "Анкеты не исчезают после ❤️ или 👎.\n"
    "❤️ — хочу на бал вместе. 👎 — не моё.\n"
    "Решение можно поменять: открой этого человека снова и нажми другую кнопку. "
    "Если уже была пара, она снимется.\n"
    "Под фото фильтры: Все, Новые, Мои ❤️, Мои 👎.\n\n"
    f"<b>{BTN_LIKES_ME}</b>\n"
    "Кто поставил тебе ❤️, а ты ещё не ответил.\n"
    "❤️ в ответ — это пара. 👎 — убрать из этого списка. "
    "В анкетах человек всё равно останется.\n\n"
    f"<b>{BTN_MATCHES}</b>\n"
    "Взаимные ❤️. «Написать» открывает чат, если у человека есть @username.\n\n"
    f"<b>{BTN_MY_PROFILE}</b>\n"
    "Посмотреть, как тебя видят. Изменить поле, скрыть анкету или удалить.\n\n"
    f"<b>{BTN_HELP}</b>\n"
    "Этот текст. То же самое — команда /help.\n\n"
    "<b>Как отменить</b>\n\n"
    f"{BTN_CANCEL} или /cancel — бросить текущий шаг и вернуться в меню. "
    "Уже сохранённая анкета на месте.\n"
    f"{BTN_BACK} — на один вопрос назад, пока заполняешь анкету.\n"
    "Любая кнопка меню внизу тоже выходит из шага и открывает свой раздел.\n"
    "Пока анкеты ещё нет, внизу кнопки шага, а не это меню. "
    "Меню появится после фото.\n\n"
    "Запутался — нажми /start. Анкета, лайки и пары не стираются."
)

REG_INTRO = (
    "<b>Дальше анкета.</b>\n"
    "Короткие шаги, на каждом написано, как вернуться.\n"
    "Меню внизу появится, когда отправишь фото."
)

CONTINUE_HIDDEN = (
    "<b>Продолжим анкету.</b>\n"
    "Прошлая версия скрыта из ленты, пока не закончишь эту.\n\n"
    f"{BTN_CANCEL} или /cancel — выйти. /start — снова с имени."
)

WELCOME_BACK_TAIL = (
    f"{BTN_BROWSE} — листать всех, ❤️ и 👎 можно менять\n"
    f"{BTN_LIKES_ME} — кто лайкнул тебя\n"
    f"{BTN_MATCHES} — взаимные, там кнопка «Написать»\n"
    f"{BTN_MY_PROFILE} — поправить или скрыть\n"
    f"{BTN_HELP} — какая кнопка за что, и как отменить шаг\n\n"
    f"{BTN_CANCEL} и /cancel — выйти из текущего шага."
)


def welcome_back(name: str) -> str:
    safe = html.escape(name.strip() or "привет")
    return f"С возвращением, <b>{safe}</b>.\n\n{WELCOME_BACK_TAIL}"


REG_DONE = (
    "<b>Анкета готова.</b> Другие уже могут её увидеть.\n\n"
    "Меню теперь внизу:\n"
    f"{BTN_BROWSE} — листать и ставить ❤️ или 👎. Решение можно менять.\n"
    f"{BTN_LIKES_ME} — кто лайкнул тебя\n"
    f"{BTN_MATCHES} — взаимные пары\n"
    f"{BTN_MY_PROFILE} — поправить или скрыть\n"
    f"{BTN_HELP} — шпаргалка\n\n"
    f"{BTN_CANCEL} и /cancel выходят из любого шага."
)

USERNAME_HINT = (
    "В Telegram нет @username — после пары кнопка «Написать» может не появиться.\n"
    "Включи его: Настройки → Имя пользователя.\n"
    "Если указал контакт вручную, в паре покажем его."
)

REG_CANCELLED = (
    f"Ок, анкету не сохранял.\n"
    f"/start — заполнить, когда будешь готов. {BTN_HELP} — как устроен бот."
)
REFILL_CANCELLED = (
    "Заполнение остановлено.\n"
    "Старая анкета скрыта, пока не закончишь новую. /start — продолжить с имени."
)
EDIT_CANCELLED = "Правку отменил. Анкета как была."
ADMIN_STEP_CANCELLED = "Админ-шаг отменён."
ALREADY_IDLE = "Ты уже в меню. Кнопки внизу, /help — шпаргалка."

FINISH_FIRST = (
    "Сначала закончи анкету — этот раздел откроется после неё.\n"
    f"Ответь на последний вопрос, {BTN_BACK} — шаг назад, "
    f"{BTN_CANCEL} или /cancel — выйти."
)

HELP_WHILE_REG = (
    "\n\nАнкета ещё не сохранена. "
    f"Ответь на последний вопрос, {BTN_BACK} или /cancel."
)
HELP_WHILE_REFILL = (
    "\n\nЗаполнение заново ещё идёт: старая анкета скрыта, пока не закончишь. "
    "Ответь на последний вопрос или /cancel."
)

# --- Регистрация ---
ASK_NAME_TITLE = "Как к тебе обращаться?"
ASK_NAME_BODY = "Имя, как на балу. Можно короткое, до 50 символов."
ASK_GENDER_TITLE = "Ты парень или девушка?"
ASK_GENDER_BODY = "Парни видят анкеты девушек, девушки — парней. Так ищем пару на танец."
ASK_LEVEL_TITLE = "Где учишься?"
ASK_LEVEL_BODY = "Сначала уровень, потом направление, курс и группа."
ASK_PROGRAM_TITLE = "Направление"
ASK_PROGRAM_BODY = "Выбери программу кнопкой."
ASK_COURSE_TITLE = "Какой курс?"
ASK_COURSE_BODY = "1, 2, 3 или 4."
ASK_GROUP_TITLE = "Группа"
ASK_GROUP_BODY = "Последний шаг учёбы — номер группы."
ASK_HEIGHT_TITLE = "Рост"
ASK_HEIGHT_BODY = "В сантиметрах, от 100 до 250. Необязательно — есть «Пропустить»."
ASK_DANCE_TITLE = "Опыт танцев"
ASK_DANCE_BODY = "Честно: на балу это полезнее роста."
ASK_ABOUT_TITLE = "Коротко о себе"
ASK_ABOUT_BODY = "От 5 до 400 символов: что танцуешь, кого ищешь, какое настроение."
ASK_PHOTO_TITLE = "Фото"
ASK_PHOTO_BODY = "Одно фото, где видно лицо. Именно фото, не файл."
ASK_CONTACT_TITLE = "Как с тобой связаться?"
ASK_CONTACT_BODY = (
    "В Telegram нет @username, после пары будет сложнее написать. "
    "Пришли @ник, телефон или «в личке». Можно пропустить."
)
MASTER_SOON = "Магистратура пока не открыта. Выбери бакалавриат — или вернись на шаг назад."

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
        return "Решение: ✨ пара — кнопка «Написать» ниже"
    return f"Решение: ✨ пара. Нет @username, id {profile.telegram_id}"


def feed_caption(profile, *, index: int, total: int, mode: str, decision: str) -> str:
    label = MODE_LABEL.get(mode, mode)
    return (
        f"{index} из {total} · {label}\n"
        f"{decision}\n\n"
        f"{format_card(profile)}\n\n"
        "← → по кругу. ❤️ и 👎 можно поменять."
    )


def feed_intro(total: int, fresh: int, *, hidden: bool) -> str:
    text = (
        f"Всего {total}. Без твоего решения — {fresh}.\n"
        "Стрелки листают по кругу, в том числе тех, кого уже видел.\n"
        "❤️ и 👎 меняют решение. Под фото: Все, Новые, Мои ❤️, Мои 👎."
    )
    if hidden:
        text += (
            "\n\nТвоя анкета скрыта: тебя не видно, смотреть других можно. "
            f"Включить — {BTN_MY_PROFILE}."
        )
    return text


FEED_EMPTY_ALL = (
    "Пока нет анкет, которые тебе подходят.\n"
    "Как только кто-то с бала заполнит анкету, он появится здесь."
)
FEED_EMPTY_NEW = (
    "Новых нет: на всех уже стоит ❤️ или 👎.\n"
    "Нажми «Все», чтобы пересмотреть и поменять решение."
)
FEED_EMPTY_LIKED = "Пока никому не поставил ❤️. Открой «Все» или «Новые»."
FEED_EMPTY_NOPE = "Список «не моё» пуст. Сюда попадают те, кому нажал 👎."

FEED_FOOTER_EMPTY = "Фильтр можно сменить кнопками ниже."

TOAST_LIKE = "❤️ Сохранил. Если ответят взаимно — придёт пара."
TOAST_MATCH = "Это пара. Кнопка «Написать» на карточке, список — в «Мои пары»."
TOAST_NOPE = "👎 Сохранил. Вернуть ❤️ можно на этой же карточке."
TOAST_UNMATCH = "Пара снята. Вернуть можно кнопкой ❤️."
TOAST_SAME = "Так и стоит. Можно листать дальше."
TOAST_WRAP = "Дальше снова первая анкета — можно пересмотреть."
TOAST_GONE = "Этой анкеты больше нет в подборке."
TOAST_CLOSED = "Карточка закрыта. Меню внизу."

# --- Входящие и пары ---
LIKES_EMPTY = (
    f"Пока никто не лайкнул.\n"
    f"Или ты уже всем ответил — тогда смотри {BTN_MATCHES} и {BTN_BROWSE}."
)


def likes_intro(n: int) -> str:
    return (
        f"Ждут ответ: {n}.\n"
        "❤️ — пара. 👎 — убрать из этого списка. "
        f"В {BTN_BROWSE} человек всё равно останется."
    )


def likes_caption(profile, *, index: int, total: int) -> str:
    return (
        f"Ждёт ответ · {index} из {total}\n\n"
        f"{format_card(profile)}\n\n"
        "❤️ в ответ — пара. 👎 — убрать отсюда."
    )


MATCH_INTRO = "Это пара. Вы оба готовы пойти на бал вместе."

MATCH_EMPTY = (
    "Пока нет взаимных ❤️.\n"
    f"Ставь ❤️ в {BTN_BROWSE}. Если человек ответит тем же, вы появитесь здесь."
)


def pairs_text(lines: list[str]) -> str:
    body = "\n".join(lines)
    return (
        f"<b>Твои пары — {len(lines)}</b>\n\n"
        f"{body}\n\n"
        f"Фото ещё раз — в {BTN_BROWSE}, фильтр «Мои ❤️»."
    )


SOMEONE_LIKED_YOU = (
    f"Кто-то лайкнул твою анкету.\n"
    f"Открой {BTN_LIKES_ME}: ❤️ в ответ создаст пару, 👎 уберёт из списка."
)


def unmatched_notice(name: str) -> str:
    safe = html.escape(name.strip() or "Человек")
    return (
        f"{safe} изменил решение. Пара больше не активна.\n"
        f"Анкета остаётся в {BTN_BROWSE} — ❤️ можно вернуть."
    )


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
CONFIRM_DELETE = (
    "Удалить анкету совсем?\n"
    "Пропадёт из ленты, лайки и пары тоже. Восстановить нельзя."
)
CONFIRM_REFILL = (
    "Заполнить анкету заново?\n"
    "Пока заполняешь, старая скрыта. Лайки и пары сбросятся, когда закончишь новую."
)
PROFILE_PAUSED = "Анкета скрыта. Тебя не показывают, смотреть других можно."
PROFILE_ACTIVE = "Анкета снова видна другим."
PROFILE_DELETED = "Анкета удалена. /start — создать новую."
NO_PROFILE = "Сначала создай анкету — нажми /start."
PROFILE_BANNED = "Доступ закрыт. Если это ошибка — напиши организаторам бала."
CHOOSE_FIELD = "Что меняем?"

# --- Админка ---
ADMIN_ONLY = "Это только для организаторов."
ADMIN_PANEL_TITLE = (
    "<b>Админка</b>\n"
    "Участники это меню не видят. /cancel — выйти в обычное меню."
)
ADMIN_PICK_VIEW = "Чью анкету открыть? Пришли id или @username, либо выбери из списка."
ADMIN_PICK_BAN = "Кого скрыть из бота? id, @username или список."
ADMIN_PICK_UNBAN = "Кого вернуть? id, @username или список."
ADMIN_BROADCAST_ASK = (
    "Пришли текст рассылки одним сообщением.\n"
    "Его получат все с открытой анкетой.\n\n"
    "/cancel — не отправлять. Кнопка меню внизу тоже отменяет."
)
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
BROADCAST_EMPTY = "Пустой текст не отправляю. Пришли сообщение или /cancel."
BROADCAST_IS_BUTTON = "Это кнопка, не текст рассылки. Пришли обычное сообщение или /cancel."
BAN_ADMIN_FORBIDDEN = "Организатора банить нельзя."
BAN_DONE = "Пользователь {tg_id} скрыт из бота."
UNBAN_DONE = "Пользователь {tg_id} снова может пользоваться ботом."
USER_NOT_FOUND = "В базе такой анкеты нет."
USERS_EMPTY = "Анкет пока нет."
USERS_BANNED_EMPTY = "Заблокированных нет."
USERS_BAN_EMPTY = "Некого банить."
USERS_PAGE = "Анкеты {start}–{end} из {total}. Нажми имя."
USER_LINE = "{n}. {name} · {gender} · {faculty}\nid {tg_id}{username}{flags}"

UNKNOWN = (
    "Не понял сообщение.\n"
    f"Кнопки внизу или /help. Если ты на середине шага — {BTN_CANCEL} или /cancel."
)
ERROR_TRY_AGAIN = "Не вышло. Попробуй ещё раз, а если повторится — /start."
STALE_BUTTON = "Это старое сообщение. Открой раздел заново кнопкой внизу."
