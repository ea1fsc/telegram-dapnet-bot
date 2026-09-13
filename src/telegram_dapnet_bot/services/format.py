import unicodedata
from datetime import datetime

DAPNET_MAX_LEN = 80

_SANITIZE_REPLACEMENTS = {
    "ñ": "n",
    "Ñ": "N",
    "'": "",
    "´": "",
    "¿": "",
    "¡": "",
    "€": "EUR",
    "$": "USD",
    "…": "...",
    "–": "-",
    "—": "-",
}


def sanitize_message_text(text: str) -> str:
    """Strip accents and pager-unfriendly glyphs, as in PagerBot."""
    normalized = unicodedata.normalize("NFD", text)
    without_marks = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    for source, target in _SANITIZE_REPLACEMENTS.items():
        without_marks = without_marks.replace(source, target)
    return without_marks.replace("\n", " ").replace("\r", " ").strip()


def format_dapnet_message(
    callsign: str,
    summary: str,
    start: datetime,
    *,
    all_day: bool = False,
) -> str:
    """Build a POCSAG-friendly page, truncated to 80 characters."""
    prefix = f"{sanitize_message_text(callsign).upper()}: "
    when = start.strftime("%d/%m") if all_day else start.strftime("%d/%m %H:%M")
    suffix = f" {when}"
    budget = DAPNET_MAX_LEN - len(prefix) - len(suffix)
    title = sanitize_message_text(summary or "Event") or "Event"
    if budget < 1:
        return (prefix + when)[:DAPNET_MAX_LEN]
    if len(title) > budget:
        title = title[:budget]
    return f"{prefix}{title}{suffix}"


def format_test_message(callsign: str) -> str:
    text = f"{sanitize_message_text(callsign).upper()}: test telegram-dapnet-bot"
    return text[:DAPNET_MAX_LEN]


def format_lead_label(minutes: int) -> str:
    if minutes <= 0:
        return "now"
    if minutes >= 10080 and minutes % 10080 == 0:
        weeks = minutes // 10080
        return "1 week" if weeks == 1 else f"{weeks} weeks"
    if minutes >= 1440 and minutes % 1440 == 0:
        days = minutes // 1440
        return "1 day" if days == 1 else f"{days} days"
    if minutes >= 60 and minutes % 60 == 0:
        hours = minutes // 60
        return "1 hour" if hours == 1 else f"{hours} hours"
    return "1 min" if minutes == 1 else f"{minutes} min"


def format_event_when(start: datetime, all_day: bool) -> str:
    return start.strftime("%d/%m") if all_day else start.strftime("%d/%m %H:%M")


def _clip(text: str, limit: int) -> str:
    cleaned = (text or "").replace("\n", " ").replace("\r", " ").strip() or "Event"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(1, limit - 3)] + "..."


def format_telegram_reminder(
    *,
    summary: str,
    start: datetime,
    offset_minutes: int,
    all_day: bool = False,
    location: str = "",
    timezone_name: str = "",
    callsign: str = "",
    destinations: list[str] | None = None,
    dapnet_text: str = "",
    dapnet_ok: bool = True,
) -> str:
    when = (
        f"{start.strftime('%d/%m/%Y')} (all day)"
        if all_day
        else start.strftime("%d/%m/%Y %H:%M")
    )
    header = (
        "Event starting now"
        if offset_minutes <= 0
        else f"Upcoming event in {format_lead_label(offset_minutes)}"
    )
    lines = [
        header,
        "",
        _clip(summary, 200),
        f"When: {when}",
    ]
    loc = (location or "").replace("\n", " ").strip()
    if loc:
        lines.append(f"Where: {_clip(loc, 200)}")
    if timezone_name:
        lines.append(f"Timezone: {timezone_name}")
    lines.append("")
    if dapnet_ok:
        dest = sanitize_message_text(callsign).upper() if callsign else "your pager"
        if destinations:
            dest = ", ".join(
                sanitize_message_text(name).upper() for name in destinations
            )
        lines.append(f"DAPNET page sent to {dest}.")
        if dapnet_text:
            lines.append(dapnet_text)
    else:
        lines.append(
            "I could not send the DAPNET page. You still have this Telegram reminder."
        )
    return "\n".join(lines)


def format_refresh_report(
    *,
    synced_ok: int,
    failed_names: list[str],
    events: list[tuple[datetime, str, bool, str]],
    window_days: int,
    limit: int = 15,
) -> str:
    lines: list[str] = []
    if failed_names:
        lines.append("I could not read: " + ", ".join(failed_names) + ".")
    if synced_ok:
        lines.append(
            f"Synced {synced_ok} calendar(s). "
            f"Upcoming events in the next {window_days} days:"
        )
    elif failed_names:
        lines.append("No calendars were synced.")
        return "\n".join(lines)
    else:
        return "No enabled calendars to sync. Use /calendars first."

    if not events:
        lines.append("No upcoming events.")
        return "\n".join(lines)

    lines.append("")
    for start, summary, all_day, calendar_name in events[:limit]:
        when = format_event_when(start, all_day)
        title = _clip(summary, 60)
        suffix = f" ({calendar_name})" if calendar_name else ""
        lines.append(f"- {when} {title}{suffix}")
    remaining = len(events) - limit
    if remaining > 0:
        lines.append(f"...and {remaining} more.")
    return "\n".join(lines)
