from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    database_url: str


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
    return Config(
        bot_token=token,
        admin_ids=frozenset(admin_ids),
        database_url=database_url,
    )
