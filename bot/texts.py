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
BTN_ADMIN = "🛠 Админка"
# --- Registration ---
ASK_NAME = "Как тебя зовут? (или как обращаться)"
ASK_GENDER = "Твой пол:"
ASK_EDU_LEVEL = "Выбери уровень:"
ASK_EDU_PROGRAM = "Выбери направление:"
ASK_EDU_COURSE = "Какой курс?"
ASK_EDU_GROUP = "Выбери группу:"
MASTER_SOON = "Магистратура — скоро появится. Пока выбери бакалавриат 🙂"
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
CANCEL = "Назад"
BACK_TO_MENU = "Назад"
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
FEED_COUNT = "Сейчас можно посмотреть {n} анкет. Листай, сравнивай — лайкай, когда определишься."
FEED_CARD_PREFIX = "Анкета {index} из {total}"
FEED_ALREADY_LIKED = "✓ Ты уже лайкнул эту анкету"
FEED_PAUSED_HINT = "Твоя анкета на паузе — тебя не показывают другим. Смотреть всё равно можно."
NO_PROFILE = "Сначала создай анкету — нажми /start."
PROFILE_BANNED = "Доступ ограничен. Если это ошибка — напиши организаторам."
BTN_LIKE = "❤️ Лайк"
BTN_PREV = "←"
BTN_NEXT = "→"
BTN_DISLIKE = "👎"
BTN_SLEEP = "💤 В меню"

# --- Likes ---
LIKES_EMPTY = "Пока никто не лайкнул. Продолжай смотреть анкеты 🙂"
LIKES_HEADER = "Те, кому ты нравишься (ещё без ответа):"
LIKE_SENT = "Лайк отправлен! Можно листать дальше и лайкнуть кого-то ещё."
LIKE_ALREADY = "Эту анкету ты уже лайкнул"
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
BTN_EDIT_FACULTY = "Группа"
BTN_EDIT_HEIGHT = "Рост"
BTN_EDIT_DANCE = "Танцы"
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
    "Совет: если в Telegram нет публичного @username "
    "(Настройки → Имя пользователя), после матча кнопка «Написать» может не появиться. "
    "Люди всё равно смогут найти тебя, если у тебя есть @ник."
)

# --- Admin ---
ADMIN_ONLY = "Команда только для админов."
ADMIN_PANEL_TITLE = "Админка. Выбери действие:"
BTN_ADMIN_STATS = "📊 Статистика"
BTN_ADMIN_USERS = "👥 Список анкет"
BTN_ADMIN_USER = "🔍 Открыть анкету"
BTN_ADMIN_BROADCAST = "📢 Рассылка"
BTN_ADMIN_BAN = "🚫 Бан"
BTN_ADMIN_UNBAN = "✅ Разбан"
BTN_ADMIN_BACK = "« В меню"
BTN_ADMIN_PICK_LIST = "📋 Выбрать из списка"
ADMIN_PICK_PROMPT = (
    "Пришли telegram id или @username.\n"
    "Или нажми «Выбрать из списка» — там по страницам."
)
ADMIN_PICK_BAN = "Кого забанить?\n\n" + ADMIN_PICK_PROMPT
ADMIN_PICK_UNBAN = "Кого разбанить?\n\n" + ADMIN_PICK_PROMPT
ADMIN_PICK_VIEW = "Чью анкету открыть?\n\n" + ADMIN_PICK_PROMPT
ADMIN_BROADCAST_ASK = "Пришли текст рассылки одним сообщением."
ADMIN_HELP = (
    "Админка:\n"
    "Кнопка «Админка» внизу или команды:\n"
    "/stats — цифры\n"
    "/users — все анкеты\n"
    "/user <id|@nick> — одна анкета\n"
    "/broadcast текст — рассылка\n"
    "/ban <id|@nick>\n"
    "/unban <id|@nick>"
)
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
BAN_USAGE = "Использование: /ban <telegram_id или @username>"
UNBAN_USAGE = "Использование: /unban <telegram_id или @username>"
BAN_DONE = "Пользователь {tg_id} забанен."
UNBAN_DONE = "Пользователь {tg_id} разбанен."
USER_NOT_FOUND = "Пользователь не найден в базе."
USERS_USAGE = (
    "Использование: /users — список, /user <telegram_id|@username> — анкета."
)
USERS_EMPTY = "Анкет пока нет."
USERS_PAGE = "Анкеты {start}–{end} из {total}:"
USERS_PICK_HINT = "Нажми на имя, чтобы выбрать."
USER_LINE = (
    "{n}. {name} · {gender} · {faculty}\n"
    "   id {tg_id}{username}{flags}"
)

# --- Misc ---
UNKNOWN = "Не понял. Жми кнопки меню или /start."
FSM_USE_BUTTONS = "Выбери вариант кнопкой ниже."
