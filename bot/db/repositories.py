from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Like, Match, Profile

ReactionResult = Literal["created", "updated", "exists", "rejected"]


@dataclass
class Stats:
    profiles: int
    active: int
    paused: int
    likes: int
    matches: int
    banned: int


@dataclass
class AddLikeResult:
    like: Like | None
    status: ReactionResult  # created/updated/exists/rejected


@dataclass
class ReactionOutcome:
    """Результат process_reaction для честного UX."""

    status: ReactionResult
    matched: bool = False


class ProfileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_tg(self, telegram_id: int) -> Profile | None:
        result = await self.session.execute(
            select(Profile).where(Profile.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Profile | None:
        uname = username.lstrip("@").strip().lower()
        if not uname:
            return None
        result = await self.session.execute(
            select(Profile).where(func.lower(Profile.username) == uname)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, profile_id: int) -> Profile | None:
        result = await self.session.execute(select(Profile).where(Profile.id == profile_id))
        return result.scalar_one_or_none()

    async def create(self, **fields: Any) -> Profile:
        profile = Profile(**fields)
        self.session.add(profile)
        try:
            await self.session.commit()
            await self.session.refresh(profile)
            return profile
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get_by_tg(int(fields["telegram_id"]))
            if existing is None:
                raise
            for key, value in fields.items():
                if key == "telegram_id":
                    continue
                setattr(existing, key, value)
            existing.is_complete = True
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

    async def upsert_complete(self, telegram_id: int, **fields: Any) -> Profile:
        existing = await self.get_by_tg(telegram_id)
        if existing:
            # Refill / незавершённая анкета: сбрасываем старый граф только при финише
            if not existing.is_complete:
                await self._delete_reactions(existing.id)
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.is_complete = True
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        return await self.create(telegram_id=telegram_id, is_complete=True, **fields)

    async def begin_refill(self, profile: Profile) -> Profile:
        """Скрываем анкету из каталога; лайки трогаем только после успешного финиша."""
        profile.is_complete = False
        profile.is_active = False
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_fields(self, profile: Profile, **fields: Any) -> Profile:
        for key, value in fields.items():
            setattr(profile, key, value)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def set_paused(self, profile: Profile, paused: bool) -> Profile:
        profile.is_active = not paused
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def delete(self, profile: Profile) -> None:
        pid = profile.id
        await self._delete_reactions(pid)
        await self.session.delete(profile)
        await self.session.commit()

    async def _delete_reactions(self, profile_id: int) -> None:
        await self.session.execute(
            delete(Match).where(
                or_(Match.profile1_id == profile_id, Match.profile2_id == profile_id)
            )
        )
        await self.session.execute(
            delete(Like).where(
                or_(
                    Like.from_profile_id == profile_id,
                    Like.to_profile_id == profile_id,
                )
            )
        )

    async def clear_reactions(self, profile: Profile) -> None:
        """Сброс лайков/матчей (legacy; refill теперь чистит в upsert_complete)."""
        await self._delete_reactions(profile.id)
        await self.session.commit()

    async def set_banned(self, telegram_id: int, banned: bool) -> Profile | None:
        profile = await self.get_by_tg(telegram_id)
        if not profile:
            return None
        profile.is_banned = banned
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def sync_username(self, profile: Profile, username: str | None) -> None:
        if profile.username != username:
            profile.username = username
            await self.session.commit()

    async def list_catalog(self, viewer: Profile) -> list[Profile]:
        """Все подходящие анкеты для просмотра (можно листать сколько угодно)."""
        looking_back = or_(
            Profile.looking_for == "any",
            Profile.looking_for == viewer.gender,
        )
        stmt = (
            select(Profile)
            .where(
                Profile.id != viewer.id,
                Profile.is_complete.is_(True),
                Profile.is_active.is_(True),
                Profile.is_banned.is_(False),
                looking_back,
            )
            .order_by(Profile.id.asc())
        )
        if viewer.looking_for != "any":
            stmt = stmt.where(Profile.gender == viewer.looking_for)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def next_feed_candidate(
        self,
        viewer: Profile,
        *,
        exclude_ids: set[int] | None = None,
    ) -> Profile | None:
        """Устарело для каталога; оставлено на случай совместимости."""
        catalog = await self.list_catalog(viewer)
        for profile in catalog:
            if exclude_ids and profile.id in exclude_ids:
                continue
            existing = await LikeRepo(self.session).get(viewer.id, profile.id)
            if existing is None:
                return profile
        return None

    async def incoming_likes(self, viewer: Profile) -> list[tuple[Profile, Like]]:
        """Кто лайкнул нас, а мы ещё не ответили (только активные анкеты)."""
        answered = select(Like.to_profile_id).where(Like.from_profile_id == viewer.id)
        stmt = (
            select(Profile, Like)
            .join(Like, Like.from_profile_id == Profile.id)
            .where(
                Like.to_profile_id == viewer.id,
                Like.is_like.is_(True),
                Profile.is_banned.is_(False),
                Profile.is_complete.is_(True),
                Profile.is_active.is_(True),
                Profile.id.not_in(answered),
            )
            .order_by(Like.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def has_pending_incoming_like(self, viewer_id: int, from_id: int) -> bool:
        """Есть ли неотвеченный лайк от from_id к viewer_id."""
        answered = await LikeRepo(self.session).get(viewer_id, from_id)
        if answered is not None:
            return False
        like = await LikeRepo(self.session).get(from_id, viewer_id)
        return bool(like and like.is_like)

    async def all_telegram_ids(
        self, *, only_complete: bool = True, only_active: bool = True
    ) -> list[int]:
        stmt = select(Profile.telegram_id).where(Profile.is_banned.is_(False))
        if only_complete:
            stmt = stmt.where(Profile.is_complete.is_(True))
        if only_active:
            stmt = stmt.where(Profile.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, *, offset: int = 0, limit: int = 10) -> list[Profile]:
        stmt = (
            select(Profile)
            .where(Profile.is_complete.is_(True))
            .order_by(Profile.id.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_banned(self, *, offset: int = 0, limit: int = 10) -> list[Profile]:
        stmt = (
            select(Profile)
            .where(Profile.is_complete.is_(True), Profile.is_banned.is_(True))
            .order_by(Profile.id.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_banned(self) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(Profile)
                .where(Profile.is_complete.is_(True), Profile.is_banned.is_(True))
            )
            or 0
        )

    async def list_bannable(
        self,
        *,
        exclude_tg_ids: frozenset[int] | set[int],
        offset: int = 0,
        limit: int = 10,
    ) -> list[Profile]:
        """Анкеты, которых можно банить (не админы)."""
        stmt = (
            select(Profile)
            .where(
                Profile.is_complete.is_(True),
                Profile.is_banned.is_(False),
            )
            .order_by(Profile.id.asc())
        )
        if exclude_tg_ids:
            stmt = stmt.where(Profile.telegram_id.not_in(exclude_tg_ids))
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_bannable(
        self, *, exclude_tg_ids: frozenset[int] | set[int]
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Profile)
            .where(
                Profile.is_complete.is_(True),
                Profile.is_banned.is_(False),
            )
        )
        if exclude_tg_ids:
            stmt = stmt.where(Profile.telegram_id.not_in(exclude_tg_ids))
        return (await self.session.scalar(stmt)) or 0

    async def count_complete(self) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(Profile)
                .where(Profile.is_complete.is_(True))
            )
            or 0
        )


class LikeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, from_id: int, to_id: int) -> Like | None:
        result = await self.session.execute(
            select(Like).where(
                Like.from_profile_id == from_id,
                Like.to_profile_id == to_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(
        self,
        from_id: int,
        to_id: int,
        *,
        is_like: bool,
    ) -> AddLikeResult:
        """Идемпотентно; dislike→like (и наоборот) обновляет запись."""
        if from_id == to_id:
            return AddLikeResult(like=None, status="rejected")

        existing = await self.get(from_id, to_id)
        if existing is not None:
            if existing.is_like == is_like:
                return AddLikeResult(like=existing, status="exists")
            existing.is_like = is_like
            existing.is_superlike = False
            await self.session.commit()
            await self.session.refresh(existing)
            return AddLikeResult(like=existing, status="updated")

        like = Like(
            from_profile_id=from_id,
            to_profile_id=to_id,
            is_like=is_like,
            is_superlike=False,
        )
        self.session.add(like)
        try:
            await self.session.commit()
            await self.session.refresh(like)
            return AddLikeResult(like=like, status="created")
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get(from_id, to_id)
            if existing is None:
                return AddLikeResult(like=None, status="rejected")
            if existing.is_like == is_like:
                return AddLikeResult(like=existing, status="exists")
            existing.is_like = is_like
            await self.session.commit()
            await self.session.refresh(existing)
            return AddLikeResult(like=existing, status="updated")

    async def has_mutual_like(self, a: int, b: int) -> bool:
        like_ab = await self.get(a, b)
        like_ba = await self.get(b, a)
        return bool(
            like_ab and like_ab.is_like and like_ba and like_ba.is_like
        )


class MatchRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _ordered(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    async def get(self, a: int, b: int) -> Match | None:
        p1, p2 = self._ordered(a, b)
        result = await self.session.execute(
            select(Match).where(Match.profile1_id == p1, Match.profile2_id == p2)
        )
        return result.scalar_one_or_none()

    async def create_if_needed(self, a: int, b: int) -> tuple[Match | None, bool]:
        """Возвращает (match, created_now)."""
        if a == b:
            return None, False
        existing = await self.get(a, b)
        if existing:
            return existing, False
        p1, p2 = self._ordered(a, b)
        match = Match(profile1_id=p1, profile2_id=p2)
        self.session.add(match)
        try:
            await self.session.commit()
            await self.session.refresh(match)
            return match, True
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get(a, b)
            return existing, False


class StatsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def collect(self) -> Stats:
        profiles = await self.session.scalar(
            select(func.count())
            .select_from(Profile)
            .where(Profile.is_complete.is_(True))
        )
        active = await self.session.scalar(
            select(func.count()).select_from(Profile).where(
                Profile.is_complete.is_(True),
                Profile.is_active.is_(True),
                Profile.is_banned.is_(False),
            )
        )
        paused = await self.session.scalar(
            select(func.count()).select_from(Profile).where(
                Profile.is_complete.is_(True),
                Profile.is_active.is_(False),
                Profile.is_banned.is_(False),
            )
        )
        likes = await self.session.scalar(
            select(func.count()).select_from(Like).where(Like.is_like.is_(True))
        )
        matches = await self.session.scalar(select(func.count()).select_from(Match))
        banned = await self.session.scalar(
            select(func.count()).select_from(Profile).where(Profile.is_banned.is_(True))
        )
        return Stats(
            profiles=profiles or 0,
            active=active or 0,
            paused=paused or 0,
            likes=likes or 0,
            matches=matches or 0,
            banned=banned or 0,
        )
