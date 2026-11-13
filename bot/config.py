from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    database_url: str
    redis_url: str | None


def normalize_database_url(url: str) -> str:
    """Railway отдаёт postgresql:// — для SQLAlchemy async нужен asyncpg."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан. Скопируй .env.example в .env и укажи токен.")

    raw_admins = os.getenv("ADMIN_IDS", "").strip()
    admin_ids: set[int] = set()
    if raw_admins:
        for part in raw_admins.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                admin_ids.add(int(part))
            except ValueError as exc:
                raise RuntimeError(
                    f"ADMIN_IDS: «{part}» не число. Укажи telegram id через запятую."
                ) from exc

    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ball_bot.db")
    )
    redis_url = os.getenv("REDIS_URL", "").strip() or None
    ensure_sqlite_parent(database_url)
    return Config(
        bot_token=token,
        admin_ids=frozenset(admin_ids),
        database_url=database_url,
        redis_url=redis_url,
    )


def ensure_sqlite_parent(url: str) -> None:
    """Папка файла SQLite создаётся заранее. Сам файл бот не удаляет."""
    if not url.startswith("sqlite"):
        return
    raw = url.split("///", 1)[-1]
    if not raw or raw == ":memory:":
        return
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_db_label(url: str) -> str:
    """Путь к sqlite или хост postgres без пароля — для лога."""
    if url.startswith("sqlite"):
        return url.split("///", 1)[-1]
    if "@" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://{rest.split('@', 1)[1]}"
    return url.split("://", 1)[0]
