from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from telegram.ext import ContextTypes

from telegram_dapnet_bot.config import Settings
from telegram_dapnet_bot.crypto import SecretBox
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import Calendar, EventCache, User
from telegram_dapnet_bot.services.dapnet import DapnetClient, DapnetError
from telegram_dapnet_bot.services.format import format_dapnet_message, format_telegram_reminder
from telegram_dapnet_bot.services.nextcloud import NextcloudError, list_events
from telegram_dapnet_bot.services.reminders import compute_offsets, effective_event_start
from telegram_dapnet_bot.services.rics import destination_callsigns

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CalendarSyncOutcome:
    name: str
    event_count: int = 0
    error: str | None = None


async def sync_user_events(
    session: AsyncSession,
    user: User,
    password: str,
    window_days: int,
    calendars: list[Calendar] | None = None,
) -> list[CalendarSyncOutcome]:
    enabled = calendars if calendars is not None else [cal for cal in user.calendars if cal.enabled]
    outcomes: list[CalendarSyncOutcome] = []
    for calendar in enabled:
        try:
            events = await list_events(
                user.nextcloud_url,
                user.nextcloud_user,
                password,
                calendar.caldav_url,
                window_days=window_days,
                timezone_name=user.timezone,
            )
        except NextcloudError as exc:
            logger.exception(
                "CalDAV sync failed for user %s calendar %s",
                user.telegram_id,
                calendar.name,
            )
            outcomes.append(CalendarSyncOutcome(name=calendar.name, error=str(exc)))
            continue

        cached = [
            EventCache(
                uid=event.uid,
                recurrence_start=event.start,
                end=event.end,
                summary=event.summary,
                location=event.location,
                etag=event.etag,
                all_day=event.all_day,
            )
            for event in events
        ]
        await repo.replace_event_cache(session, user.id, calendar.id, cached)
        outcomes.append(CalendarSyncOutcome(name=calendar.name, event_count=len(cached)))
    return outcomes


async def sync_all_users(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    factory: async_sessionmaker[AsyncSession] = context.application.bot_data[
        "session_factory"
    ]
    box: SecretBox = context.application.bot_data["secret_box"]

    async with factory() as session:
        users = await repo.list_approved_users_with_calendars(session)
        for user in users:
            password = box.decrypt(user.nextcloud_password_encrypted)
            outcomes = await sync_user_events(
                session, user, password, settings.fetch_event_window_days
            )
            for outcome in outcomes:
                if outcome.error is None:
                    continue
                try:
                    await context.bot.send_message(
                        user.telegram_id,
                        "I could not read your Nextcloud calendars. "
                        "Check the URL or app password with /register.",
                    )
                except Exception:
                    logger.debug("Could not notify user about CalDAV error")
        await session.commit()


async def dispatch_due_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    factory: async_sessionmaker[AsyncSession] = context.application.bot_data[
        "session_factory"
    ]
    dapnet: DapnetClient = context.application.bot_data["dapnet"]
    now = datetime.now(timezone.utc)
    grace = timedelta(minutes=settings.misfire_grace_minutes)

    async with factory() as session:
        users = await repo.list_approved_users_with_calendars(session)
        for user in users:
            if not any(cal.enabled for cal in user.calendars):
                continue
            try:
                offsets = compute_offsets(user.lead_minutes, user.repeat_count)
            except ValueError:
                logger.warning("Invalid reminder settings for user %s", user.telegram_id)
                continue
            events = await repo.list_events_for_user(session, user.id)
            for event in events:
                start_local = effective_event_start(event, user.timezone)
                for offset in offsets:
                    fire_at = start_local - timedelta(minutes=offset)
                    fire_at_utc = fire_at.astimezone(timezone.utc)
                    if fire_at_utc > now or now - fire_at_utc > grace:
                        continue
                    already = await repo.reminder_already_sent(
                        session,
                        user.id,
                        event.uid,
                        event.recurrence_start,
                        offset,
                    )
                    if already:
                        continue
                    text = format_dapnet_message(
                        user.dapnet_callsign,
                        event.summary,
                        start_local,
                        all_day=event.all_day,
                    )
                    destinations = destination_callsigns(user)
                    dapnet_ok = False
                    try:
                        await dapnet.send_call(
                            text,
                            destinations,
                            user.tx_group,
                            server=user.dapnet_server,
                        )
                        dapnet_ok = True
                    except DapnetError:
                        logger.exception(
                            "DAPNET send failed for user %s event %s",
                            user.telegram_id,
                            event.uid,
                        )

                    telegram_ok = False
                    telegram_text = format_telegram_reminder(
                        summary=event.summary,
                        start=start_local,
                        offset_minutes=offset,
                        all_day=event.all_day,
                        location=event.location,
                        timezone_name=user.timezone,
                        callsign=user.dapnet_callsign,
                        destinations=destinations,
                        dapnet_text=text,
                        dapnet_ok=dapnet_ok,
                    )
                    try:
                        await context.bot.send_message(user.telegram_id, telegram_text)
                        telegram_ok = True
                    except Exception:
                        logger.exception(
                            "Telegram reminder failed for user %s event %s",
                            user.telegram_id,
                            event.uid,
                        )

                    if not dapnet_ok and not telegram_ok:
                        continue
                    await repo.mark_reminder_sent(
                        session,
                        user.id,
                        event.uid,
                        event.recurrence_start,
                        offset,
                    )
                    logger.info(
                        "Reminded %s for %s offset=%s dapnet=%s telegram=%s",
                        user.dapnet_callsign,
                        event.summary,
                        offset,
                        dapnet_ok,
                        telegram_ok,
                    )
        await session.commit()
