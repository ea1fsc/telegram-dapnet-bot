from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

import caldav

logger = logging.getLogger(__name__)


class NextcloudError(Exception):
    pass


@dataclass(frozen=True)
class CalendarInfo:
    name: str
    url: str


@dataclass(frozen=True)
class CalendarEvent:
    uid: str
    start: datetime
    end: datetime | None
    summary: str
    location: str
    etag: str
    all_day: bool


def normalize_caldav_url(url: str) -> str:
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        raise NextcloudError("The Nextcloud URL is empty")
    if cleaned.startswith("file:"):
        raise NextcloudError("Only http(s) URLs are allowed")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    if "/remote.php/dav" not in cleaned:
        cleaned = f"{cleaned}/remote.php/dav"
    return cleaned


def _as_aware(value: datetime | date, timezone_name: str) -> tuple[datetime, bool]:
    tz = ZoneInfo(timezone_name)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=tz), False
        return value, False
    return datetime.combine(value, time.min, tzinfo=tz), True


def _extract_event(raw, timezone_name: str) -> CalendarEvent | None:
    try:
        component = raw.icalendar_component
    except Exception:
        logger.debug("Skipping unreadable calendar object", exc_info=True)
        return None

    status = str(component.get("status", "")).upper()
    if status == "CANCELLED":
        return None

    uid = str(component.get("uid") or "").strip()
    if not uid:
        return None

    try:
        dtstart = component.decoded("dtstart")
    except Exception:
        return None

    start, all_day = _as_aware(dtstart, timezone_name)
    end = None
    if "dtend" in component:
        try:
            end, _ = _as_aware(component.decoded("dtend"), timezone_name)
        except Exception:
            end = None

    summary = str(component.get("summary") or "Event").strip()
    location = str(component.get("location") or "").strip()
    etag = str(getattr(raw, "etag", "") or "")
    return CalendarEvent(
        uid=uid,
        start=start,
        end=end,
        summary=summary,
        location=location,
        etag=etag,
        all_day=all_day,
    )


def _client(url: str, username: str, password: str) -> caldav.DAVClient:
    return caldav.DAVClient(url=url, username=username, password=password, timeout=30)


def _list_calendars_sync(url: str, username: str, password: str) -> list[CalendarInfo]:
    try:
        client = _client(url, username, password)
        principal = client.principal()
        calendars = principal.calendars()
    except Exception as exc:
        raise NextcloudError(f"Could not connect to Nextcloud: {exc}") from exc

    result: list[CalendarInfo] = []
    for calendar in calendars:
        name = calendar.name or str(calendar.url).rstrip("/").split("/")[-1]
        result.append(CalendarInfo(name=str(name), url=str(calendar.url)))
    return result


def _list_events_sync(
    dav_url: str,
    username: str,
    password: str,
    calendar_url: str,
    start: datetime,
    end: datetime,
    timezone_name: str,
) -> list[CalendarEvent]:
    try:
        client = _client(dav_url, username, password)
        calendar = client.calendar(url=calendar_url)
        raw_events = calendar.search(
            start=start, end=end, event=True, expand=True
        )
    except Exception as exc:
        raise NextcloudError(f"Could not read events: {exc}") from exc

    events: list[CalendarEvent] = []
    for raw in raw_events:
        parsed = _extract_event(raw, timezone_name)
        if parsed is not None:
            events.append(parsed)
    return events


async def list_calendars(url: str, username: str, password: str) -> list[CalendarInfo]:
    return await asyncio.to_thread(_list_calendars_sync, url, username, password)


async def list_events(
    dav_url: str,
    username: str,
    password: str,
    calendar_url: str,
    *,
    window_days: int,
    timezone_name: str,
) -> list[CalendarEvent]:
    now = datetime.now(ZoneInfo(timezone_name))
    start = now - timedelta(hours=1)
    end = now + timedelta(days=window_days)
    return await asyncio.to_thread(
        _list_events_sync,
        dav_url,
        username,
        password,
        calendar_url,
        start,
        end,
        timezone_name,
    )


async def probe_connection(url: str, username: str, password: str) -> list[CalendarInfo]:
    return await list_calendars(url, username, password)
