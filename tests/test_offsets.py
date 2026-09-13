from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from telegram_dapnet_bot.db.models import EventCache
from telegram_dapnet_bot.services.nextcloud import normalize_caldav_url
from telegram_dapnet_bot.services.reminders import compute_offsets, effective_event_start


def test_single_reminder() -> None:
    assert compute_offsets(60, 1) == [60, 0]


def test_three_evenly_spaced_reminders() -> None:
    assert compute_offsets(60, 3) == [60, 40, 20, 0]


def test_two_reminders_truncate_minutes() -> None:
    assert compute_offsets(15, 2) == [15, 7, 0]


def test_offsets_reject_invalid_values() -> None:
    with pytest.raises(ValueError):
        compute_offsets(0, 1)
    with pytest.raises(ValueError):
        compute_offsets(30, 0)


def test_all_day_uses_nine_local() -> None:
    event = EventCache(
        uid="evt-1",
        recurrence_start=datetime(2026, 9, 7, 0, 0, tzinfo=ZoneInfo("UTC")),
        all_day=True,
        summary="Festivo",
    )
    start = effective_event_start(event, "Europe/Madrid")
    assert start.hour == 9
    assert start.tzinfo == ZoneInfo("Europe/Madrid")
    assert start.date().isoformat() == "2026-09-07"


def test_timed_event_keeps_instant() -> None:
    event = EventCache(
        uid="evt-2",
        recurrence_start=datetime(2026, 9, 7, 16, 0, tzinfo=ZoneInfo("UTC")),
        all_day=False,
        summary="QSO",
    )
    start = effective_event_start(event, "Europe/Madrid")
    assert start.hour == 18


def test_normalize_nextcloud_url() -> None:
    assert (
        normalize_caldav_url("https://cloud.example.org")
        == "https://cloud.example.org/remote.php/dav"
    )
    assert (
        normalize_caldav_url("cloud.example.org/")
        == "https://cloud.example.org/remote.php/dav"
    )
