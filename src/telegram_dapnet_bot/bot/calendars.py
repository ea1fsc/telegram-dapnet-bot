from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from telegram_dapnet_bot.bot.access import require_approved, session_factory_of
from telegram_dapnet_bot.bot.keyboards import calendars_keyboard
from telegram_dapnet_bot.config import Settings
from telegram_dapnet_bot.crypto import SecretBox
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import User, UserStatus
from telegram_dapnet_bot.db.session import session_scope
from telegram_dapnet_bot.services.format import format_refresh_report
from telegram_dapnet_bot.services.nextcloud import NextcloudError, list_calendars
from telegram_dapnet_bot.services.reminders import effective_event_start
from telegram_dapnet_bot.services.scheduler import sync_user_events


def _calendar_text(calendars) -> str:
    if not calendars:
        return (
            "I found no calendars on your account. "
            "Tap refresh or check your credentials with /register."
        )
    return (
        "Choose which calendars to sync.\n"
        "ON = DAPNET page + Telegram reminder. OFF = ignored."
    )


async def build_refresh_report(context: ContextTypes.DEFAULT_TYPE, user: User) -> str:
    settings: Settings = context.application.bot_data["settings"]
    box: SecretBox = context.application.bot_data["secret_box"]
    async with session_scope(session_factory_of(context)) as session:
        db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
        assert db_user is not None
        calendars = await repo.list_calendars(session, db_user.id)
        enabled = [calendar for calendar in calendars if calendar.enabled]
        if not enabled:
            return format_refresh_report(
                synced_ok=0,
                failed_names=[],
                events=[],
                window_days=settings.fetch_event_window_days,
            )
        outcomes = await sync_user_events(
            session,
            db_user,
            box.decrypt(db_user.nextcloud_password_encrypted),
            settings.fetch_event_window_days,
            calendars=enabled,
        )
        now = datetime.now(timezone.utc)
        upcoming: list[tuple[datetime, str, bool, str]] = []
        for event in await repo.list_events_for_user(session, db_user.id):
            start_local = effective_event_start(event, db_user.timezone)
            if start_local.astimezone(timezone.utc) < now:
                continue
            calendar_name = event.calendar.name if event.calendar is not None else ""
            upcoming.append(
                (start_local, event.summary, event.all_day, calendar_name)
            )
        upcoming.sort(key=lambda item: item[0])
        return format_refresh_report(
            synced_ok=sum(1 for outcome in outcomes if outcome.error is None),
            failed_names=[outcome.name for outcome in outcomes if outcome.error],
            events=upcoming,
            window_days=settings.fetch_event_window_days,
        )


@require_approved
async def calendars_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    async with session_scope(session_factory_of(context)) as session:
        db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
        assert db_user is not None
        calendars = await repo.list_calendars(session, db_user.id)
    await update.effective_message.reply_text(
        _calendar_text(calendars),
        reply_markup=calendars_keyboard(calendars),
    )


@require_approved
async def refresh_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    await update.effective_message.reply_text(await build_refresh_report(context, user))


async def calendars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg_user = update.effective_user
    if query is None or tg_user is None:
        return
    await query.answer()

    data = query.data or ""
    async with session_scope(session_factory_of(context)) as session:
        user = await repo.get_user_by_telegram_id(session, tg_user.id)
        if user is None or user.status != UserStatus.APPROVED:
            await query.edit_message_text("You need an approved account.")
            return

        report_user = user
        if data == "cal:events":
            pass
        elif data == "cal:refresh":
            box: SecretBox = context.application.bot_data["secret_box"]
            try:
                remote = await list_calendars(
                    user.nextcloud_url,
                    user.nextcloud_user,
                    box.decrypt(user.nextcloud_password_encrypted),
                )
            except NextcloudError as exc:
                await query.edit_message_text(f"I could not refresh the list: {exc}")
                return
            calendars = await repo.sync_calendar_catalog(
                session, user, [(item.name, item.url) for item in remote]
            )
        elif data.startswith("cal:toggle:"):
            calendar_id = int(data.split(":")[-1])
            calendar = await repo.get_calendar(session, calendar_id)
            if calendar is None or calendar.user_id != user.id:
                await query.edit_message_text("Calendar not found.")
                return
            await repo.toggle_calendar(session, calendar)
            calendars = await repo.list_calendars(session, user.id)
        else:
            return

    if data == "cal:events":
        if query.message is None:
            return
        await query.message.reply_text(await build_refresh_report(context, report_user))
        return

    await query.edit_message_text(
        _calendar_text(calendars),
        reply_markup=calendars_keyboard(calendars),
    )
