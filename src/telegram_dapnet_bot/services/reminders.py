from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram_dapnet_bot.db.models import EventCache


def compute_offsets(lead_minutes: int, repeat_count: int) -> list[int]:
    """Spread `repeat_count` reminders from T-lead, plus one at event start (T-0)."""
    if lead_minutes < 1:
        raise ValueError("lead_minutes must be >= 1")
    if repeat_count < 1:
        raise ValueError("repeat_count must be >= 1")
    offsets = [
        int(lead_minutes * (repeat_count - index) / repeat_count)
        for index in range(repeat_count)
    ]
    ahead = [offset for offset in offsets if offset > 0]
    return [*ahead, 0]


def effective_event_start(event: EventCache, timezone_name: str) -> datetime:
    """All-day events fire relative to 09:00 in the user's timezone."""
    tz = ZoneInfo(timezone_name)
    if event.all_day:
        local_date = event.recurrence_start.astimezone(tz).date()
        return datetime.combine(local_date, time(9, 0), tzinfo=tz)
    start = event.recurrence_start
    if start.tzinfo is None:
        return start.replace(tzinfo=tz)
    return start.astimezone(tz)
