from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Profile(Base):
    """Анкета участника бала."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    name: Mapped[str] = mapped_column(String(50))
    gender: Mapped[str] = mapped_column(String(16))  # male | female
    looking_for: Mapped[str] = mapped_column(String(16))  # male | female | any
    faculty: Mapped[str] = mapped_column(String(100))
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dance_experience: Mapped[str] = mapped_column(String(16))  # none | some | confident
    goal: Mapped[str] = mapped_column(String(32))  # full_evening | waltz_tango | company
    about: Mapped[str] = mapped_column(String(400))
    photo_file_id: Mapped[str] = mapped_column(String(512))
    contact: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # False = на паузе
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    likes_sent: Mapped[list["Like"]] = relationship(
        back_populates="from_profile",
        foreign_keys="Like.from_profile_id",
        cascade="all, delete-orphan",
    )
    likes_received: Mapped[list["Like"]] = relationship(
        back_populates="to_profile",
        foreign_keys="Like.to_profile_id",
        cascade="all, delete-orphan",
    )


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("from_profile_id", "to_profile_id", name="uq_like_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    to_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    is_like: Mapped[bool] = mapped_column(Boolean, default=True)  # False = дизлайк
    is_superlike: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    from_profile: Mapped["Profile"] = relationship(
        back_populates="likes_sent", foreign_keys=[from_profile_id]
    )
    to_profile: Mapped["Profile"] = relationship(
        back_populates="likes_received", foreign_keys=[to_profile_id]
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("profile1_id", "profile2_id", name="uq_match_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile1_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    profile2_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
