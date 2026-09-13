from datetime import datetime, timezone

import pytest

from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import EventCache, UserStatus
from telegram_dapnet_bot.db.session import create_engine, create_session_factory, init_db


@pytest.fixture
async def session():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_and_approve_user(session) -> None:
    user = await repo.upsert_user(
        session,
        telegram_id=42,
        telegram_username="ea1abc",
        dapnet_callsign="ea1abc",
        nextcloud_url="https://cloud.example.org/remote.php/dav",
        nextcloud_user="alice",
        nextcloud_password_encrypted="cipher",
        timezone="Europe/Madrid",
        tx_group="all",
        lead_minutes=60,
        repeat_count=2,
        status=UserStatus.PENDING,
    )
    assert user.status == UserStatus.PENDING
    updated = await repo.set_user_status(session, 42, UserStatus.APPROVED)
    assert updated is not None
    assert updated.status == UserStatus.APPROVED


@pytest.mark.asyncio
async def test_calendar_toggle_and_event_cache(session) -> None:
    user = await repo.upsert_user(
        session,
        telegram_id=7,
        telegram_username=None,
        dapnet_callsign="ea2xyz",
        nextcloud_url="https://cloud.example.org/remote.php/dav",
        nextcloud_user="bob",
        nextcloud_password_encrypted="cipher",
        timezone="Europe/Madrid",
        tx_group="all",
        lead_minutes=60,
        repeat_count=1,
        status=UserStatus.APPROVED,
    )
    calendars = await repo.sync_calendar_catalog(
        session, user, [("Personal", "https://cloud.example.org/cal/personal/")]
    )
    assert len(calendars) == 1
    assert calendars[0].enabled is False
    toggled = await repo.toggle_calendar(session, calendars[0])
    assert toggled.enabled is True

    start = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
    await repo.replace_event_cache(
        session,
        user.id,
        toggled.id,
        [
            EventCache(
                uid="evt-1",
                recurrence_start=start,
                summary="QSO",
                all_day=False,
            )
        ],
    )
    events = await repo.list_events_for_user(session, user.id)
    assert len(events) == 1
    assert events[0].summary == "QSO"

    assert not await repo.reminder_already_sent(session, user.id, "evt-1", start, 60)
    await repo.mark_reminder_sent(session, user.id, "evt-1", start, 60)
    assert await repo.reminder_already_sent(session, user.id, "evt-1", start, 60)


@pytest.mark.asyncio
async def test_delete_user_removes_calendars_events_and_reminders(session) -> None:
    user = await repo.upsert_user(
        session,
        telegram_id=99,
        telegram_username="gone",
        dapnet_callsign="ea9zzz",
        nextcloud_url="https://cloud.example.org/remote.php/dav",
        nextcloud_user="gone",
        nextcloud_password_encrypted="cipher",
        timezone="Europe/Madrid",
        tx_group="all",
        lead_minutes=60,
        repeat_count=1,
        status=UserStatus.APPROVED,
    )
    calendars = await repo.sync_calendar_catalog(
        session, user, [("Personal", "https://cloud.example.org/cal/personal/")]
    )
    start = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
    await repo.replace_event_cache(
        session,
        user.id,
        calendars[0].id,
        [
            EventCache(
                uid="evt-del",
                recurrence_start=start,
                summary="QSO",
                all_day=False,
            )
        ],
    )
    await repo.mark_reminder_sent(session, user.id, "evt-del", start, 60)
    user_id = user.id
    await repo.delete_user(session, user)
    assert await repo.get_user_by_telegram_id(session, 99) is None
    assert await repo.list_calendars(session, user_id) == []
    assert await repo.list_events_for_user(session, user_id) == []
    assert await repo.list_user_rics(session, user_id) == []


def _user_kwargs(**overrides):
    data = dict(
        telegram_username=None,
        nextcloud_url="https://cloud.example.org/remote.php/dav",
        nextcloud_user="alice",
        nextcloud_password_encrypted="cipher",
        timezone="Europe/Madrid",
        tx_group="all",
        lead_minutes=60,
        repeat_count=1,
        status=UserStatus.APPROVED,
    )
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_user_rics_and_shared_catalog(session) -> None:
    user_a = await repo.upsert_user(
        session, telegram_id=1, dapnet_callsign="ea1aaa", **_user_kwargs()
    )
    user_b = await repo.upsert_user(
        session, telegram_id=2, dapnet_callsign="ea1bbb", **_user_kwargs()
    )
    await repo.add_user_ric(session, user_a, 145904, "ea4hqf", source="manual")
    catalog = await repo.get_catalog_ric(session, 145904)
    assert catalog is not None
    assert catalog.callsign == "ea4hqf"
    await repo.add_user_ric(
        session, user_b, 145904, catalog.callsign, source="catalog"
    )
    rows = await repo.list_user_rics(session, user_b.id)
    assert len(rows) == 1
    assert rows[0].ric == 145904
    assert rows[0].callsign == "ea4hqf"


@pytest.mark.asyncio
async def test_backfill_user_rics_from_csv(session) -> None:
    user = await repo.upsert_user(
        session,
        telegram_id=3,
        dapnet_callsign="ea1ccc",
        dapnet_rics="145904,2080905",
        **_user_kwargs(),
    )
    await repo.backfill_user_rics_from_csv(session)
    rows = await repo.list_user_rics(session, user.id)
    assert [row.ric for row in rows] == [145904, 2080905]
    assert all(row.callsign == "ea1ccc" for row in rows)
