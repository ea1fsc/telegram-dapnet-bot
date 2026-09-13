from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from telegram_dapnet_bot.db.models import (
    Calendar,
    EventCache,
    RicCatalog,
    SentReminder,
    User,
    UserRic,
    UserStatus,
)


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    result = await session.execute(
        select(User)
        .options(selectinload(User.rics))
        .where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars())


async def list_pending_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User)
        .where(User.status == UserStatus.PENDING)
        .order_by(User.created_at.asc())
    )
    return list(result.scalars())


async def list_approved_users_with_calendars(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User)
        .options(selectinload(User.calendars), selectinload(User.rics))
        .where(User.status == UserStatus.APPROVED)
    )
    return list(result.scalars())


async def upsert_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    telegram_username: str | None,
    dapnet_callsign: str,
    dapnet_rics: str = "",
    nextcloud_url: str,
    nextcloud_user: str,
    nextcloud_password_encrypted: str,
    timezone: str,
    tx_group: str,
    dapnet_server: str = "de",
    lead_minutes: int,
    repeat_count: int,
    status: UserStatus,
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
    user.telegram_username = telegram_username
    user.dapnet_callsign = dapnet_callsign
    user.dapnet_rics = dapnet_rics
    user.nextcloud_url = nextcloud_url
    user.nextcloud_user = nextcloud_user
    user.nextcloud_password_encrypted = nextcloud_password_encrypted
    user.timezone = timezone
    user.tx_group = tx_group
    user.dapnet_server = dapnet_server
    user.lead_minutes = lead_minutes
    user.repeat_count = repeat_count
    user.status = status
    await session.flush()
    return user


async def set_user_status(
    session: AsyncSession, telegram_id: int, status: UserStatus
) -> User | None:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return None
    user.status = status
    await session.flush()
    return user


async def update_reminder_settings(
    session: AsyncSession, user: User, lead_minutes: int | None, repeat_count: int | None
) -> User:
    if lead_minutes is not None:
        user.lead_minutes = lead_minutes
    if repeat_count is not None:
        user.repeat_count = repeat_count
    await session.flush()
    return user


async def update_timezone(session: AsyncSession, user: User, timezone: str) -> User:
    user.timezone = timezone
    await session.flush()
    return user


async def update_tx_groups(session: AsyncSession, user: User, tx_group: str) -> User:
    user.tx_group = tx_group
    await session.flush()
    return user


async def update_dapnet_server(session: AsyncSession, user: User, server: str) -> User:
    user.dapnet_server = server
    await session.flush()
    return user


async def list_calendars(session: AsyncSession, user_id: int) -> list[Calendar]:
    result = await session.execute(
        select(Calendar).where(Calendar.user_id == user_id).order_by(Calendar.name)
    )
    return list(result.scalars())


async def get_calendar(session: AsyncSession, calendar_id: int) -> Calendar | None:
    return await session.get(Calendar, calendar_id)


async def sync_calendar_catalog(
    session: AsyncSession,
    user: User,
    catalogs: list[tuple[str, str]],
) -> list[Calendar]:
    existing = {cal.caldav_url: cal for cal in await list_calendars(session, user.id)}
    seen: set[str] = set()
    for name, url in catalogs:
        seen.add(url)
        calendar = existing.get(url)
        if calendar is None:
            calendar = Calendar(
                user_id=user.id, caldav_url=url, name=name, enabled=False
            )
            session.add(calendar)
        else:
            calendar.name = name
    for url, calendar in existing.items():
        if url not in seen:
            await session.delete(calendar)
    await session.flush()
    return await list_calendars(session, user.id)


async def toggle_calendar(session: AsyncSession, calendar: Calendar) -> Calendar:
    calendar.enabled = not calendar.enabled
    if not calendar.enabled:
        await session.execute(
            delete(EventCache).where(EventCache.calendar_id == calendar.id)
        )
    await session.flush()
    return calendar


async def replace_event_cache(
    session: AsyncSession,
    user_id: int,
    calendar_id: int,
    events: list[EventCache],
) -> None:
    await session.execute(delete(EventCache).where(EventCache.calendar_id == calendar_id))
    for event in events:
        event.user_id = user_id
        event.calendar_id = calendar_id
        session.add(event)
    await session.flush()


async def list_events_for_user(session: AsyncSession, user_id: int) -> list[EventCache]:
    result = await session.execute(
        select(EventCache)
        .options(selectinload(EventCache.calendar))
        .where(EventCache.user_id == user_id)
        .order_by(EventCache.recurrence_start)
    )
    return list(result.scalars())


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.execute(
        delete(SentReminder).where(SentReminder.user_id == user.id)
    )
    await session.execute(delete(EventCache).where(EventCache.user_id == user.id))
    await session.execute(delete(Calendar).where(Calendar.user_id == user.id))
    await session.execute(delete(UserRic).where(UserRic.user_id == user.id))
    await session.delete(user)
    await session.flush()


async def reminder_already_sent(
    session: AsyncSession,
    user_id: int,
    uid: str,
    recurrence_start: datetime,
    offset_minutes: int,
) -> bool:
    result = await session.execute(
        select(SentReminder.id).where(
            SentReminder.user_id == user_id,
            SentReminder.uid == uid,
            SentReminder.recurrence_start == recurrence_start,
            SentReminder.offset_minutes == offset_minutes,
        )
    )
    return result.scalar_one_or_none() is not None


async def mark_reminder_sent(
    session: AsyncSession,
    user_id: int,
    uid: str,
    recurrence_start: datetime,
    offset_minutes: int,
) -> None:
    session.add(
        SentReminder(
            user_id=user_id,
            uid=uid,
            recurrence_start=recurrence_start,
            offset_minutes=offset_minutes,
        )
    )
    await session.flush()


async def get_catalog_ric(session: AsyncSession, ric: int) -> RicCatalog | None:
    return await session.get(RicCatalog, ric)


async def list_ric_catalog(session: AsyncSession) -> list[RicCatalog]:
    result = await session.execute(select(RicCatalog).order_by(RicCatalog.ric))
    return list(result.scalars())


async def upsert_catalog_ric(
    session: AsyncSession, ric: int, callsign: str
) -> RicCatalog:
    row = await get_catalog_ric(session, ric)
    name = callsign.strip().lower()
    if row is None:
        row = RicCatalog(ric=ric, callsign=name)
        session.add(row)
    else:
        row.callsign = name
    await session.flush()
    return row


async def list_user_rics(session: AsyncSession, user_id: int) -> list[UserRic]:
    result = await session.execute(
        select(UserRic).where(UserRic.user_id == user_id).order_by(UserRic.ric)
    )
    return list(result.scalars())


async def get_user_ric(session: AsyncSession, ric_row_id: int) -> UserRic | None:
    return await session.get(UserRic, ric_row_id)


async def add_user_ric(
    session: AsyncSession,
    user: User,
    ric: int,
    callsign: str,
    *,
    source: str = "manual",
    enabled: bool = True,
) -> UserRic:
    name = callsign.strip().lower()
    await upsert_catalog_ric(session, ric, name)
    existing = await session.execute(
        select(UserRic).where(UserRic.user_id == user.id, UserRic.ric == ric)
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = UserRic(
            user_id=user.id,
            ric=ric,
            callsign=name,
            source=source,
            enabled=enabled,
        )
        session.add(row)
    else:
        row.callsign = name
        row.source = source
        row.enabled = enabled
    await session.flush()
    user.dapnet_rics = ",".join(
        str(item.ric) for item in await list_user_rics(session, user.id)
    )
    return row


async def replace_user_rics(
    session: AsyncSession,
    user: User,
    items: list[tuple[int, str, str]],
) -> list[UserRic]:
    await session.execute(delete(UserRic).where(UserRic.user_id == user.id))
    rows: list[UserRic] = []
    for ric, callsign, source in items:
        rows.append(
            await add_user_ric(session, user, ric, callsign, source=source, enabled=True)
        )
    if not items:
        user.dapnet_rics = ""
        await session.flush()
    return rows


async def toggle_user_ric(session: AsyncSession, row: UserRic) -> UserRic:
    row.enabled = not row.enabled
    await session.flush()
    return row


async def remove_user_ric(session: AsyncSession, user: User, row: UserRic) -> None:
    await session.delete(row)
    await session.flush()
    user.dapnet_rics = ",".join(
        str(item.ric) for item in await list_user_rics(session, user.id)
    )


async def backfill_user_rics_from_csv(session: AsyncSession) -> None:
    from telegram_dapnet_bot.services.radioid import process_dmr_id

    users = await list_users(session)
    for user in users:
        existing = await list_user_rics(session, user.id)
        if existing:
            continue
        for part in (user.dapnet_rics or "").split(","):
            ric = process_dmr_id(part.strip())
            if ric <= 0:
                continue
            catalog = await get_catalog_ric(session, ric)
            callsign = catalog.callsign if catalog else user.dapnet_callsign
            await add_user_ric(
                session, user, ric, callsign, source="radioid", enabled=True
            )

