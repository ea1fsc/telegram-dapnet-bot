from telegram import Update
from telegram.ext import ContextTypes

from telegram_dapnet_bot.bot.access import require_approved, session_factory_of
from telegram_dapnet_bot.bot.keyboards import reminders_keyboard
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import User, UserStatus
from telegram_dapnet_bot.db.session import session_scope
from telegram_dapnet_bot.services.reminders import compute_offsets


def _reminders_text(lead_minutes: int, repeat_count: int) -> str:
    offsets = compute_offsets(lead_minutes, repeat_count)
    pretty = ", ".join(
        "at event time" if minutes == 0 else f"T-{minutes} min" for minutes in offsets
    )
    return (
        "When and how often I notify you before each event, "
        "plus one alert at event time "
        "(DAPNET page and Telegram message).\n"
        f"Lead time: {lead_minutes} min · Repeats: {repeat_count}\n"
        f"Alerts: {pretty}"
    )


@require_approved
async def reminders_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    await update.effective_message.reply_text(
        _reminders_text(user.lead_minutes, user.repeat_count),
        reply_markup=reminders_keyboard(user.lead_minutes, user.repeat_count),
    )


async def reminders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg_user = update.effective_user
    if query is None or tg_user is None:
        return
    await query.answer()

    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "rem":
        return

    async with session_scope(session_factory_of(context)) as session:
        user = await repo.get_user_by_telegram_id(session, tg_user.id)
        if user is None or user.status != UserStatus.APPROVED:
            await query.edit_message_text("You need an approved account.")
            return
        if parts[1] == "lead":
            await repo.update_reminder_settings(session, user, int(parts[2]), None)
        elif parts[1] == "count":
            await repo.update_reminder_settings(session, user, None, int(parts[2]))
        await session.refresh(user)
        lead, count = user.lead_minutes, user.repeat_count

    await query.edit_message_text(
        _reminders_text(lead, count),
        reply_markup=reminders_keyboard(lead, count),
    )
