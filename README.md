# Бот поиска пары на студенческий бал

Telegram-бот в духе ленты анкет (лайк / дизлайк / суперлайк / матч),
но только для одного события — бала. Не дейтинг «навсегда».

## Стек

- Python 3.11+
- aiogram 3.x
- SQLite + SQLAlchemy (async) + aiosqlite
- FSM для регистрации и редактирования анкеты

## Быстрый старт

### 1. Токен у @BotFather

1. Открой Telegram → [@BotFather](https://t.me/BotFather)
2. `/newbot` → имя и username бота
3. Скопируй токен вида `123456:ABC-DEF...`

Узнай свой Telegram id у [@userinfobot](https://t.me/userinfobot) — он понадобится для админки.

### 2. Установка

```bash
cd date_bot_for_sa
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Отредактируй `.env`:

```env
BOT_TOKEN=твой_токен
ADMIN_IDS=твой_telegram_id
DATABASE_URL=sqlite+aiosqlite:///./ball_bot.db
```

### 3. Запуск

```bash
python -m bot.main
```

Бот работает long polling. Остановка — `Ctrl+C`.
Файл БД `ball_bot.db` появится рядом с проектом при первом запуске.

## Возможности

| Раздел | Что делает |
|--------|------------|
| Регистрация | Пошаговая анкета: имя, пол, кого ищет, курс/фак, рост, танцы, цель на бале, о себе, фото |
| Смотреть анкеты | Карточка + ❤️ / 👎 / ⭐ / 💤 |
| Кому я нравлюсь | Входящие лайки (суперлайки выше), ответ → матч |
| Моя анкета | Просмотр, редактирование, пауза, удаление, заполнить заново |
| Матч | Оба получают анкету и кнопку «Написать» (если есть @username) |

Фильтр ленты взаимный: ты ищешь X, и кандидат ищет твой пол (или «неважно»).

## Админка

Только для `ADMIN_IDS` из `.env`:

- `/stats` — анкеты, лайки, матчи
- `/broadcast текст` — рассылка всем с анкетой (или `/broadcast` и текст следующим сообщением)
- `/ban <telegram_id>` / `/unban <telegram_id>`

## Структура

```
bot/
  main.py           # точка входа
  config.py         # .env
  texts.py          # все тексты
  services.py       # карточки, лайки, матчи
  handlers/         # start, profile, feed, likes, match, admin
  keyboards/
  states/
  db/               # models + repositories + session
  middlewares/      # сессия БД, бан
```

Схема таблиц: `profiles`, `likes`, `matches` — создаётся автоматически при старте (`Base.metadata.create_all`).

## Замечания для оргкомитета

- Один бал — один бот / одна БД. Меняй тексты в `bot/texts.py` (`BALL_NAME` и формулировки).
- Попроси участников открыть @username или указать контакт вручную — иначе после матча связь сложнее.
- Для продакшена на сервере удобен `systemd` / `screen` / `tmux`; Redis FSM не обязателен для небольшого вуза.
