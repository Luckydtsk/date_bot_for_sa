"""Логика ленты, пар и тексты, которые видит человек."""

import inspect
from datetime import date
from types import SimpleNamespace

import pytest

from bot import texts as t
from bot.config import safe_db_label
from bot.db.repositories import LikeRepo, MatchRepo, ProfileRepo
from bot.db.session import init_db, make_engine, make_session_factory
from bot.education import format_group, intake_year_short
from bot.handlers import setup_routers
from bot.keyboards.common import feed_controls_kb, likes_kb, main_menu_kb
from bot.services import can_see, process_reaction


class FakeBot:
    def __init__(self) -> None:
        self.out: list[tuple] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.out.append(("message", chat_id, text))
        return SimpleNamespace(message_id=len(self.out))

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        self.out.append(("photo", chat_id, caption))
        return SimpleNamespace(message_id=len(self.out))


@pytest.fixture
async def session(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/t.db"
    engine = make_engine(url)
    await init_db(engine)
    factory = make_session_factory(engine)
    async with factory() as db:
        yield db
    await engine.dispose()


async def add(session, tg: int, gender: str, **extra):
    looking = "female" if gender == "male" else "male"
    fields = dict(
        telegram_id=tg,
        username=f"user{tg}",
        name="Аня" if gender == "female" else "Илья",
        gender=gender,
        looking_for=looking,
        faculty="И-26-1",
        height=170,
        dance_experience="some",
        goal="full_evening",
        about="Люблю вальс и спокойный вечер",
        photo_file_id=f"photo-{tg}",
        contact=None,
        is_active=True,
        is_banned=False,
        is_complete=True,
    )
    fields.update(extra)
    return await ProfileRepo(session).create(**fields)


def test_guide_names_every_control():
    guide = t.HELP_FULL
    for label in (
        t.BTN_BROWSE,
        t.BTN_LIKES_ME,
        t.BTN_MATCHES,
        t.BTN_MY_PROFILE,
        t.BTN_HELP,
        t.BTN_BACK,
        t.BTN_CANCEL,
    ):
        assert label in guide
    assert "/start" not in guide
    assert "/help" not in guide
    assert "/cancel" not in guide
    assert "поменять" in guide
    assert "по кругу" in guide
    assert len(guide) < 700

    back = t.welcome_back("Маша")
    assert t.BTN_HELP in back
    assert "<b>Маша</b>" in back
    assert "/start" not in back
    assert "/cancel" not in t.REG_DONE


def test_step_tells_how_to_leave():
    first = t.step(1, 10, "Имя", "Как зовут", back=False)
    later = t.step(4, 10, "Курс", "Выбери", back=True)
    assert t.BTN_CANCEL in first
    assert "/cancel" not in first
    assert t.BTN_BACK not in first
    assert t.BTN_BACK in later
    assert "<b>Шаг 4 из 10</b>" in later
    assert "/cancel" not in later


def test_card_escapes_html_and_fits_caption():
    nasty = SimpleNamespace(
        name="<b>хак</b>",
        gender="female",
        faculty="И&Ю",
        dance_experience="none",
        height=168,
        about="текст <script>",
        username="ann",
        telegram_id=5,
    )
    card = t.format_card(nasty)
    assert "<script>" not in card
    assert "&lt;script&gt;" in card
    assert "&amp;" in card
    assert "<b>&lt;b&gt;хак&lt;/b&gt;</b>" in card

    huge = SimpleNamespace(
        name="Я" * 50,
        gender="male",
        faculty="Ю" * 100,
        dance_experience="confident",
        height=250,
        about="а" * 400,
        username=None,
        telegram_id=99,
    )
    caption = t.feed_caption(
        huge, index=12, total=120, mode="all", decision=t.decision_match(huge)
    )
    assert len(caption) <= 1024
    assert "Группа:" in caption
    assert "ещё не смотрел" not in caption


def test_menu_buttons_do_not_repeat_and_callbacks_fit():
    labels = [button.text for row in main_menu_kb(is_admin=True).keyboard for button in row]
    assert len(labels) == len(set(labels))
    feed = [button.text for row in feed_controls_kb().keyboard for button in row]
    assert t.BTN_BACK in feed
    assert t.FEED_NEXT in feed
    assert t.BTN_LIKE in feed
    assert t.BTN_NOPE in feed
    assert t.FEED_LIKED in feed
    assert t.FEED_DISLIKED in feed
    assert t.BTN_WRITE not in feed
    assert t.BTN_CLOSE not in feed
    callbacks = [
        button.callback_data
        for row in likes_kb(15).inline_keyboard
        for button in row
        if button.callback_data
    ]
    assert callbacks
    assert all(len(item.encode()) <= 64 for item in callbacks)


def test_faculty_question_is_free_text():
    blob = " ".join(
        (
            t.ASK_FACULTY_TITLE,
            t.ASK_FACULTY_BODY,
            t.ASK_LEVEL_BODY,
            t.HELP_FULL,
        )
    )
    for program in ("РИС", "МПБЭ", "ИЯ"):
        assert program not in blob
    assert "кнопк" not in t.ASK_FACULTY_BODY.lower()


def test_group_year_follows_the_school_year():
    assert intake_year_short(1, today=date(2026, 11, 13)) == 26
    assert intake_year_short(2, today=date(2026, 11, 13)) == 25
    assert intake_year_short(1, today=date(2026, 7, 1)) == 25
    assert format_group("И", 1, 2) == f"И-{intake_year_short(1)}-2"


def test_database_label_hides_password_and_startup_does_not_drop():
    label = safe_db_label("postgresql+asyncpg://user:secret@db.internal:5432/ball")
    assert "secret" not in label
    assert "db.internal" in label
    source = inspect.getsource(init_db)
    assert "create_all" in source
    assert "drop_all" not in source
    assert "drop" not in source


def test_routers_build():
    root = setup_routers()
    assert root.sub_routers


async def test_catalog_keeps_seen_profiles_and_filters(session):
    male = await add(session, 1, "male")
    girls = [await add(session, 10 + i, "female", name=f"Аня{i}") for i in range(3)]
    await add(session, 2, "male", name="Другой")
    hidden = await add(session, 20, "female", name="Скрытая", is_active=False)

    repo = ProfileRepo(session)
    everyone = await repo.list_catalog(male, "all")
    assert [p.id for p in everyone] == [g.id for g in girls]
    assert hidden.id not in {p.id for p in everyone}
    assert all(p.gender == "female" for p in everyone)

    fresh = await repo.list_catalog(male, "new")
    assert [p.id for p in fresh] == [g.id for g in girls]

    await LikeRepo(session).add(male.id, girls[0].id, is_like=True)
    await LikeRepo(session).add(male.id, girls[1].id, is_like=False)

    assert [p.id for p in await repo.list_catalog(male, "new")] == [girls[2].id]
    assert [p.id for p in await repo.list_catalog(male, "liked")] == [girls[0].id]
    assert [p.id for p in await repo.list_catalog(male, "nope")] == [girls[1].id]
    # «Все» не выкидывает тех, кому уже ответил — их можно пересмотреть.
    assert [p.id for p in await repo.list_catalog(male, "all")] == [g.id for g in girls]


async def test_like_can_be_changed_and_match_comes_off(session):
    ilya = await add(session, 1, "male", name="Илья")
    anya = await add(session, 2, "female", name="Аня")
    bot = FakeBot()

    created = await process_reaction(bot, session, ilya, anya, is_like=True)
    assert created.status == "created"
    assert created.matched is False
    assert any(item[0] == "message" and item[1] == anya.telegram_id for item in bot.out)

    again = await process_reaction(bot, session, ilya, anya, is_like=True)
    assert again.status == "exists"

    back = await process_reaction(bot, session, anya, ilya, is_like=True)
    assert back.matched is True
    assert await MatchRepo(session).get(ilya.id, anya.id) is not None
    assert any(item[0] == "photo" for item in bot.out)

    changed = await process_reaction(bot, session, ilya, anya, is_like=False)
    assert changed.unmatched is True
    assert await MatchRepo(session).get(ilya.id, anya.id) is None
    assert [p.id for p in await ProfileRepo(session).list_catalog(ilya, "nope")] == [anya.id]
    assert await ProfileRepo(session).list_catalog(ilya, "liked") == []
    assert any("Аня" not in item[2] and "Илья" in item[2] for item in bot.out if item[0] == "message")

    restored = await process_reaction(bot, session, ilya, anya, is_like=True)
    assert restored.matched is True
    assert await MatchRepo(session).partners(ilya.id)
    assert not can_see(ilya, ilya)


async def test_same_gender_like_is_rejected(session):
    one = await add(session, 1, "male", name="Один")
    two = await add(session, 2, "male", name="Два")
    outcome = await process_reaction(FakeBot(), session, one, two, is_like=True)
    assert outcome.status == "rejected"
    assert await LikeRepo(session).get(one.id, two.id) is None


async def test_restart_keeps_profiles(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/ball.db"
    engine = make_engine(url)
    await init_db(engine)
    factory = make_session_factory(engine)
    async with factory() as session:
        await add(session, 7, "female", name="Лена")
    await engine.dispose()

    engine = make_engine(url)
    await init_db(engine)
    factory = make_session_factory(engine)
    async with factory() as session:
        found = await ProfileRepo(session).get_by_tg(7)
        assert found is not None
        assert found.name == "Лена"
        assert await ProfileRepo(session).count_complete() == 1
    await engine.dispose()
