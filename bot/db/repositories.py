from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Like, Match, Profile

ReactionResult = Literal["created", "exists", "rejected"]


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
    status: ReactionResult  # created = новая запись; exists = уже была; rejected = отказ


class ProfileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_tg(self, telegram_id: int) -> Profile | None:
        result = await self.session.execute(
            select(Profile).where(Profile.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, profile_id: int) -> Profile | None:
        result = await self.session.execute(select(Profile).where(Profile.id == profile_id))
        return result.scalar_one_or_none()

    async def create(self, **fields: Any) -> Profile:
        profile = Profile(**fields)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def upsert_complete(self, telegram_id: int, **fields: Any) -> Profile:
        existing = await self.get_by_tg(telegram_id)
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.is_complete = True
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        return await self.create(telegram_id=telegram_id, is_complete=True, **fields)

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
        await self.session.execute(
            delete(Match).where(
                or_(Match.profile1_id == pid, Match.profile2_id == pid)
            )
        )
        await self.session.execute(
            delete(Like).where(
                or_(Like.from_profile_id == pid, Like.to_profile_id == pid)
            )
        )
        await self.session.delete(profile)
        await self.session.commit()

    async def clear_reactions(self, profile: Profile) -> None:
        """Сброс лайков/матчей при заполнении анкеты заново."""
        pid = profile.id
        await self.session.execute(
            delete(Match).where(
                or_(Match.profile1_id == pid, Match.profile2_id == pid)
            )
        )
        await self.session.execute(
            delete(Like).where(
                or_(Like.from_profile_id == pid, Like.to_profile_id == pid)
            )
        )
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

    async def next_feed_candidate(
        self,
        viewer: Profile,
        *,
        exclude_ids: set[int] | None = None,
    ) -> Profile | None:
        """Следующая анкета: взаимный фильтр по полу, не своя, не оценённая, активная."""
        rated_subq = select(Like.to_profile_id).where(Like.from_profile_id == viewer.id)

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
                Profile.id.not_in(rated_subq),
                looking_back,
            )
            .order_by(func.random())
            .limit(1)
        )
        if viewer.looking_for != "any":
            stmt = stmt.where(Profile.gender == viewer.looking_for)

        if exclude_ids:
            stmt = stmt.where(Profile.id.notin_(exclude_ids))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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

    async def all_telegram_ids(self, *, only_active: bool = True) -> list[int]:
        stmt = select(Profile.telegram_id).where(Profile.is_banned.is_(False))
        if only_active:
            stmt = stmt.where(Profile.is_complete.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


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
        """
        Идемпотентная реакция: повторный клик не переписывает лайк в дизлайк.
        """
        if from_id == to_id:
            return AddLikeResult(like=None, status="rejected")

        existing = await self.get(from_id, to_id)
        if existing is not None:
            return AddLikeResult(like=existing, status="exists")

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
            return AddLikeResult(like=existing, status="exists")

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
        profiles = await self.session.scalar(select(func.count()).select_from(Profile))
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
