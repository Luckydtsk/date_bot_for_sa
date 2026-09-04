"""Тексты бота. Дружелюбно, коротко, без канцелярита."""

BALL_NAME = "студенческий бал"

# --- Start / onboarding ---
WELCOME_NEW = (
    f"Привет! Это бот для поиска пары на {BALL_NAME}.\n\n"
    "Давай создадим твою анкету 👇"
)
WELCOME_BACK = "С возвращением! Что делаем?"
START_HAS_PROFILE = "У тебя уже есть анкета. Открываю меню."

# --- Main menu ---
MENU_TITLE = "Главное меню"
BTN_BROWSE = "👀 Смотреть анкеты"
BTN_MY_PROFILE = "📝 Моя анкета"
BTN_LIKES_ME = "💘 Кому я нравлюсь"
# --- Registration ---
ASK_NAME = "Как тебя зовут? (или как обращаться)"
ASK_GENDER = "Твой пол:"
ASK_FACULTY = "Курс и факультет (или откуда ты). Например: «3 курс, Истфак»"
ASK_HEIGHT = (
    "Рост в см — по желанию.\n"
    "Напиши число или нажми «Пропустить»."
)
ASK_DANCE = "Опыт танцев?"
ASK_ABOUT = (
    "Коротко о себе — до 400 символов.\n"
    "Что любишь танцевать, какой партнёр нужен, настроение 🙂"
)
ASK_PHOTO = "Пришли одно фото для анкеты (именно фото, не файл)."
ASK_CONTACT = (
    "У тебя скрыт username в Telegram — после матча сложно будет связаться.\n"
    "Напиши контакт вручную: @ник, телефон или «напиши в ЛС по id».\n"
    "Или нажми «Пропустить» — тогда в матче будет только Telegram id."
)

NAME_TOO_LONG = "Слишком длинное имя. Максимум 50 символов."
FACULTY_TOO_LONG = "Слишком длинно. Максимум 100 символов."
ABOUT_TOO_LONG = "О себе — максимум 400 символов. Сократи чуть-чуть."
ABOUT_TOO_SHORT = "Хотя бы пару слов напиши (от 5 символов)."
NEED_PHOTO = "Нужно именно фото. Пришли картинку как фото, не как документ."
NEED_TEXT = "Напиши текстом, пожалуйста."
INVALID_HEIGHT = "Рост — число от 100 до 250, либо «Пропустить»."
REG_DONE = "Анкета готова! Можно смотреть других 👀"
REG_CANCELLED = "Ок, регистрацию прервали. Нажми /start, когда будешь готов."

# --- Gender / dance labels ---
GENDER_MALE = "Парень"
GENDER_FEMALE = "Девушка"
DANCE_NONE = "Нет опыта"
DANCE_SOME = "Немного"
DANCE_CONFIDENT = "Уверенно"

SKIP = "Пропустить"
CANCEL = "Отмена"
BACK_TO_MENU = "В меню"
YES = "Да"
NO = "Нет"

# --- Profile card ---
def format_card(profile) -> str:
    dance = {
        "none": "нет",
        "some": "немного",
        "confident": "уверенно",
    }.get(profile.dance_experience, profile.dance_experience)

    lines = [
        f"{profile.name}, {profile.faculty}",
        f"Танцы: {dance}",
    ]
    if profile.height:
        lines.insert(1, f"Рост: {profile.height} см")
    lines.append(f"О себе: {profile.about}")
    return "\n".join(lines)

# --- Feed ---
FEED_EMPTY = (
    "Пока анкет больше нет.\n"
    "Загляни позже или позови друзей — чем больше анкет, тем легче найти пару."
)
FEED_PAUSED_HINT = "Твоя анкета на паузе — тебя не показывают другим. Смотреть всё равно можно."
NO_PROFILE = "Сначала создай анкету — нажми /start."
PROFILE_BANNED = "Доступ ограничен. Если это ошибка — напиши организаторам."
BTN_LIKE = "❤️"
BTN_DISLIKE = "👎"
BTN_SLEEP = "💤"

# --- Likes ---
LIKES_EMPTY = "Пока никто не лайкнул. Продолжай смотреть анкеты 🙂"
LIKES_HEADER = "Те, кому ты нравишься (ещё без ответа):"
LIKE_SENT = "Лайк отправлен!"
DISLIKE_DONE = "Ок, дальше."
SOMEONE_LIKED_YOU = "Кто-то лайкнул твою анкету! Загляни в «💘 Кому я нравлюсь»."

# --- Match ---
MATCH_TITLE = "Это матч! 🎉\nВы оба готовы познакомиться ради бала."
MATCH_CONTACT_USERNAME = "Написать: @{username}"
MATCH_CONTACT_MANUAL = "Контакт: {contact}"
MATCH_CONTACT_ID = (
    "Username скрыт. Telegram id: {tg_id}\n"
    "Можно найти через поиск или попросить организаторов помочь связаться."
)
BTN_WRITE = "✉️ Написать"
BTN_MATCH_OK = "Круто!"

# --- My profile ---
MY_PROFILE_HEADER = "Твоя анкета:"
BTN_EDIT = "✏️ Редактировать"
BTN_EDIT_NAME = "Имя"
BTN_EDIT_GENDER = "Пол"
BTN_EDIT_FACULTY = "Курс / факультет"
BTN_EDIT_HEIGHT = "Рост"
BTN_EDIT_DANCE = "Опыт танцев"
BTN_EDIT_ABOUT = "О себе"
BTN_EDIT_PHOTO = "Фото"
BTN_EDIT_CONTACT = "Контакт"
BTN_REFILL = "🔄 Заполнить заново"
BTN_PAUSE = "💤 Скрыть анкету"
BTN_UNPAUSE = "✅ Показать анкету"
BTN_DELETE = "🗑 Удалить анкету"
PROFILE_PAUSED = "Анкета скрыта — тебя не показывают в ленте."
PROFILE_ACTIVE = "Анкета снова видна другим."
PROFILE_DELETED = "Анкета удалена. /start — создать новую."
CONFIRM_DELETE = "Точно удалить анкету? Это необратимо."
CONFIRM_REFILL = "Заполнить анкету заново? Старые данные заменятся."
EDIT_DONE = "Обновили!"
CHOOSE_FIELD = "Что поменять?"

USERNAME_MISSING_WARN = (
    "⚠️ У тебя нет публичного @username. "
    "После матча другому человеку будет сложнее написать.\n"
    "Открой настройки Telegram → имя пользователя, или укажи контакт в анкете."
)

# --- Admin ---
ADMIN_ONLY = "Команда только для админов."
STATS_TEMPLATE = (
    "📊 Статистика\n\n"
    "Анкет: {profiles}\n"
    "Активных: {active}\n"
    "На паузе: {paused}\n"
    "Лайков: {likes}\n"
    "Матчей: {matches}\n"
    "Забанено: {banned}"
)
BROADCAST_USAGE = "Использование: /broadcast текст сообщения"
BROADCAST_DONE = "Рассылка завершена: {ok} ок, {fail} ошибок из {total}."
BAN_USAGE = "Использование: /ban <telegram_id>"
UNBAN_USAGE = "Использование: /unban <telegram_id>"
BAN_DONE = "Пользователь {tg_id} забанен."
UNBAN_DONE = "Пользователь {tg_id} разбанен."
USER_NOT_FOUND = "Пользователь не найден в базе."
USERS_USAGE = "Использование: /users — список анкет, /user <telegram_id> — одна анкета."
USERS_EMPTY = "Анкет пока нет."
USERS_PAGE = "Анкеты {start}–{end} из {total}:"
USER_LINE = (
    "{n}. {name} · {gender} · {faculty}\n"
    "   id {tg_id}{username}{flags}"
)

# --- Misc ---
UNKNOWN = "Не понял. Жми кнопки меню или /start."
FSM_USE_BUTTONS = "Выбери вариант кнопкой ниже."
