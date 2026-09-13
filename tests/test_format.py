from datetime import datetime
from zoneinfo import ZoneInfo

from telegram_dapnet_bot.services.format import (
    DAPNET_MAX_LEN,
    format_dapnet_message,
    format_test_message,
)


def test_format_includes_callsign_and_time() -> None:
    start = datetime(2026, 9, 7, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_dapnet_message("ea1abc", "Reunion", start)
    assert text.startswith("EA1ABC: ")
    assert "07/09 18:00" in text
    assert "Reunion" in text
    assert len(text) <= DAPNET_MAX_LEN


def test_format_all_day_omits_clock() -> None:
    start = datetime(2026, 9, 7, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_dapnet_message("ea1abc", "Festivo", start, all_day=True)
    assert text == "EA1ABC: Festivo 07/09"


def test_format_truncates_long_summary() -> None:
    start = datetime(2026, 9, 7, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_dapnet_message("ea1abc", "X" * 200, start)
    assert len(text) == DAPNET_MAX_LEN
    assert text.endswith("18:00")


def test_format_strips_accents_like_pagerbot() -> None:
    from telegram_dapnet_bot.services.format import sanitize_message_text

    start = datetime(2026, 9, 7, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    assert sanitize_message_text("Reunión en el café") == "Reunion en el cafe"
    text = format_dapnet_message("ea1abc", "Reunión ¿hoy?", start)
    assert "Reunion hoy" in text
    assert "¿" not in text


def test_format_test_message_fits() -> None:
    text = format_test_message("ea4xyz")
    assert text.startswith("EA4XYZ:")
    assert len(text) <= DAPNET_MAX_LEN


def test_format_lead_label() -> None:
    from telegram_dapnet_bot.services.format import format_lead_label

    assert format_lead_label(0) == "now"
    assert format_lead_label(15) == "15 min"
    assert format_lead_label(60) == "1 hour"
    assert format_lead_label(180) == "3 hours"
    assert format_lead_label(1440) == "1 day"
    assert format_lead_label(10080) == "1 week"


def test_format_telegram_reminder_includes_event_and_dapnet() -> None:
    from telegram_dapnet_bot.services.format import format_telegram_reminder

    start = datetime(2026, 9, 7, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_telegram_reminder(
        summary="Reunión",
        start=start,
        offset_minutes=60,
        location="Club",
        timezone_name="Europe/Madrid",
        callsign="ea1abc",
        dapnet_text="EA1ABC: Reunion 07/09 18:00",
        dapnet_ok=True,
    )
    assert "Upcoming event in 1 hour" in text
    assert "Reunión" in text
    assert "07/09/2026 18:00" in text
    assert "Where: Club" in text
    assert "DAPNET page sent to EA1ABC." in text
    assert "EA1ABC: Reunion 07/09 18:00" in text


def test_format_telegram_reminder_at_event_time() -> None:
    from telegram_dapnet_bot.services.format import format_telegram_reminder

    start = datetime(2026, 9, 7, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_telegram_reminder(
        summary="QSO",
        start=start,
        offset_minutes=0,
        callsign="ea1abc",
        dapnet_ok=True,
    )
    assert "Event starting now" in text
    assert "Upcoming event" not in text


def test_format_telegram_reminder_all_day_without_dapnet() -> None:
    from telegram_dapnet_bot.services.format import format_telegram_reminder

    start = datetime(2026, 9, 7, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_telegram_reminder(
        summary="Festivo",
        start=start,
        offset_minutes=1440,
        all_day=True,
        dapnet_ok=False,
    )
    assert "Upcoming event in 1 day" in text
    assert "(all day)" in text
    assert "I could not send the DAPNET page" in text


def test_format_refresh_report_lists_events() -> None:
    from telegram_dapnet_bot.services.format import format_refresh_report

    start = datetime(2026, 9, 13, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    text = format_refresh_report(
        synced_ok=1,
        failed_names=[],
        events=[(start, "Meeting", False, "Personal")],
        window_days=14,
    )
    assert "Synced 1 calendar(s)" in text
    assert "- 13/09 18:00 Meeting (Personal)" in text


def test_format_refresh_report_no_enabled_calendars() -> None:
    from telegram_dapnet_bot.services.format import format_refresh_report

    text = format_refresh_report(
        synced_ok=0,
        failed_names=[],
        events=[],
        window_days=14,
    )
    assert "No enabled calendars" in text
    assert "/calendars" in text
