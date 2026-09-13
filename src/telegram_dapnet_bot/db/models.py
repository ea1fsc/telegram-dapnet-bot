from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dapnet_callsign: Mapped[str] = mapped_column(String(32), index=True)
    dapnet_rics: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[UserStatus] = mapped_column(String(16), default=UserStatus.PENDING)
    nextcloud_url: Mapped[str] = mapped_column(String(512))
    nextcloud_user: Mapped[str] = mapped_column(String(255))
    nextcloud_password_encrypted: Mapped[str] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Madrid")
    tx_group: Mapped[str] = mapped_column(String(512), default="all")
    dapnet_server: Mapped[str] = mapped_column(String(8), default="de")
    lead_minutes: Mapped[int] = mapped_column(Integer, default=60)
    repeat_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    calendars: Mapped[list["Calendar"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    events: Mapped[list["EventCache"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sent_reminders: Mapped[list["SentReminder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    rics: Mapped[list["UserRic"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RicCatalog(Base):
    __tablename__ = "rics"

    ric: Mapped[int] = mapped_column(Integer, primary_key=True)
    callsign: Mapped[str] = mapped_column(String(32))


class UserRic(Base):
    __tablename__ = "user_rics"
    __table_args__ = (UniqueConstraint("user_id", "ric"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    ric: Mapped[int] = mapped_column(Integer, index=True)
    callsign: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(16), default="manual")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="rics")


class Calendar(Base):
    __tablename__ = "calendars"
    __table_args__ = (UniqueConstraint("user_id", "caldav_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    caldav_url: Mapped[str] = mapped_column(String(1024))
    name: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="calendars")
    events: Mapped[list["EventCache"]] = relationship(
        back_populates="calendar", cascade="all, delete-orphan"
    )


class EventCache(Base):
    __tablename__ = "event_cache"
    __table_args__ = (UniqueConstraint("user_id", "uid", "recurrence_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    calendar_id: Mapped[int] = mapped_column(
        ForeignKey("calendars.id", ondelete="CASCADE")
    )
    uid: Mapped[str] = mapped_column(String(512))
    recurrence_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str] = mapped_column(String(512), default="")
    location: Mapped[str] = mapped_column(String(512), default="")
    etag: Mapped[str] = mapped_column(String(255), default="")
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="events")
    calendar: Mapped[Calendar] = relationship(back_populates="events")


class SentReminder(Base):
    __tablename__ = "sent_reminders"
    __table_args__ = (
        UniqueConstraint("user_id", "uid", "recurrence_start", "offset_minutes"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    uid: Mapped[str] = mapped_column(String(512))
    recurrence_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    offset_minutes: Mapped[int] = mapped_column(Integer)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sent_reminders")
