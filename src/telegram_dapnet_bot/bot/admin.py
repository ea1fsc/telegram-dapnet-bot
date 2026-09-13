from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from telegram_dapnet_bot.bot.access import is_admin, require_admin, session_factory_of, UNKNOWN_COMMAND_TEXT
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import UserStatus
from telegram_dapnet_bot.db.session import session_scope

logger = logging.getLogger(__name__)


@require_admin
async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    async with session_scope(session_factory_of(context)) as session:
        users = await repo.list_pending_users(session)
    if not users:
        await update.effective_message.reply_text("There are no pending requests.")
        return
    lines = [
        f"- {user.telegram_id} {user.dapnet_callsign} "
        f"(@{user.telegram_username or '-'})"
        f"{' RIC ' + user.dapnet_rics if user.dapnet_rics else ''}"
        for user in users
    ]
    await update.effective_message.reply_text("Pending:\n" + "\n".join(lines))


@require_admin
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    async with session_scope(session_factory_of(context)) as session:
        users = await repo.list_users(session)
    if not users:
        await update.effective_message.reply_text("There are no users.")
        return
    lines = [
        f"- {user.telegram_id} {user.dapnet_callsign} [{user.status}]"
        for user in users[:50]
    ]
    await update.effective_message.reply_text("Users:\n" + "\n".join(lines))


@require_admin
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_status_from_args(update, context, UserStatus.APPROVED)


@require_admin
async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_status_from_args(update, context, UserStatus.REJECTED)


async def _set_status_from_args(
    update: Update, context: ContextTypes.DEFAULT_TYPE, status: UserStatus
) -> None:
    if update.effective_message is None:
        return
    if not context.args:
        command = "approve" if status == UserStatus.APPROVED else "reject"
        await update.effective_message.reply_text(f"Usage: /{command} <telegram_id>")
        return
    try:
        telegram_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("The Telegram id must be numeric.")
        return
    await _apply_status(update, context, telegram_id, status)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    await query.answer()
    if not is_admin(context, user.id):
        await query.edit_message_text(UNKNOWN_COMMAND_TEXT)
        return
    try:
        _, action, raw_id = (query.data or "").split(":", 2)
        telegram_id = int(raw_id)
    except ValueError:
        await query.edit_message_text("Invalid callback.")
        return
    status = UserStatus.APPROVED if action == "approve" else UserStatus.REJECTED
    await _apply_status(update, context, telegram_id, status, from_callback=True)


async def _apply_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    telegram_id: int,
    status: UserStatus,
    *,
    from_callback: bool = False,
) -> None:
    async with session_scope(session_factory_of(context)) as session:
        user = await repo.set_user_status(session, telegram_id, status)
    target = update.effective_message
    if user is None:
        if target:
            await target.reply_text("I could not find that user.")
        return

    verb = "approved" if status == UserStatus.APPROVED else "rejected"
    summary = f"User {telegram_id} ({user.dapnet_callsign}) {verb}."
    if from_callback and update.callback_query:
        await update.callback_query.edit_message_text(summary)
    elif target:
        await target.reply_text(summary)

    try:
        if status == UserStatus.APPROVED:
            await context.bot.send_message(
                telegram_id,
                "Your account has been approved.\n"
                "Use /help for the command menu. "
                "Pick calendars with /calendars and destination RICs with /rics. "
                "I will page DAPNET and also message you here before events.",
            )
        else:
            await context.bot.send_message(
                telegram_id,
                "Your request has been rejected. "
                "If that was a mistake, register again with /register.",
            )
    except Exception:
        logger.debug("Could not notify user %s about status change", telegram_id)
