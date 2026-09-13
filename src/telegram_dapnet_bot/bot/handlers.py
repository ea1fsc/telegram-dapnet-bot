from __future__ import annotations

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_dapnet_bot.bot.access import (
    UNKNOWN_COMMAND_TEXT,
    is_admin,
    load_user,
    require_approved,
    session_factory_of,
)
from telegram_dapnet_bot.bot.account import delete_callback, delete_command
from telegram_dapnet_bot.bot.admin import (
    admin_callback,
    approve_command,
    pending_command,
    reject_command,
    users_command,
)
from telegram_dapnet_bot.bot.calendars import calendars_callback, calendars_command, refresh_command
from telegram_dapnet_bot.bot.help_menu import build_help
from telegram_dapnet_bot.bot.register import build_register_handler
from telegram_dapnet_bot.bot.reminders import reminders_callback, reminders_command
from telegram_dapnet_bot.bot.rics import build_rics_handler, rics_callback, rics_command
from telegram_dapnet_bot.bot.txgroup import (
    server_callback,
    server_command,
    txgroup_callback,
    txgroup_command,
)
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import User, UserStatus
from telegram_dapnet_bot.db.session import session_scope
from telegram_dapnet_bot.services.dapnet import DapnetClient, DapnetError
from telegram_dapnet_bot.services.format import format_test_message
from telegram_dapnet_bot.services.rics import destination_callsigns, format_ric_label
from telegram_dapnet_bot.services.txgroups import SERVER_LABELS, parse_tx_groups

logger = logging.getLogger(__name__)

USER_BOT_COMMANDS = [
    BotCommand("start", "Start and help"),
    BotCommand("help", "Command menu"),
    BotCommand("register", "Register DAPNET and Nextcloud"),
    BotCommand("status", "Account status"),
    BotCommand("calendars", "Choose calendars"),
    BotCommand("reminders", "Lead time and reminder count"),
    BotCommand("txgroup", "Transmitter groups"),
    BotCommand("server", "DAPNET core EA/DL"),
    BotCommand("rics", "Choose destination RICs"),
    BotCommand("timezone", "Timezone"),
    BotCommand("test", "Send a test page"),
    BotCommand("refresh", "Reload upcoming events"),
    BotCommand("delete", "Erase your data"),
    BotCommand("cancel", "Cancel registration"),
]

ADMIN_BOT_COMMANDS = [
    BotCommand("pending", "Pending registrations"),
    BotCommand("users", "List users"),
    BotCommand("approve", "Approve a Telegram user id"),
    BotCommand("reject", "Reject a Telegram user id"),
]


async def _send_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    tg_user = update.effective_user
    if message is None or tg_user is None:
        return
    db_user = await load_user(context, tg_user.id)
    text, keyboard = build_help(
        db_user.status if db_user is not None else None,
        is_admin=is_admin(context, tg_user.id),
    )
    await message.reply_text(text, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_help(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_help(update, context)


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg_user = update.effective_user
    if query is None or tg_user is None:
        return
    action = (query.data or "").split(":", 1)[-1]
    if action == "register":
        await query.answer()
        if update.effective_message:
            await update.effective_message.reply_text(
                "Send /register to start, or /cancel if you are already registering."
            )
        return
    await query.answer()
    handlers = {
        "status": status_command,
        "calendars": calendars_command,
        "reminders": reminders_command,
        "txgroup": txgroup_command,
        "server": server_command,
        "rics": rics_command,
        "timezone": timezone_command,
        "test": test_command,
        "refresh": refresh_command,
        "delete": delete_command,
        "pending": pending_command,
        "users": users_command,
    }
    handler = handlers.get(action)
    if handler is None:
        return
    await handler(update, context)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(UNKNOWN_COMMAND_TEXT)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    db_user = await load_user(context, user.id)
    if db_user is None:
        await message.reply_text("You are not registered. Use /register.")
        return
    labels = {
        UserStatus.PENDING: "pending approval",
        UserStatus.APPROVED: "approved",
        UserStatus.REJECTED: "rejected",
    }
    ric_lines = [
        format_ric_label(item.ric, item.callsign, enabled=item.enabled)
        for item in (db_user.rics or [])
    ]
    ric_text = ", ".join(ric_lines) if ric_lines else (db_user.dapnet_rics or "—")
    await message.reply_text(
        f"Status: {labels.get(db_user.status, db_user.status)}\n"
        f"Callsign: {db_user.dapnet_callsign}\n"
        f"RICs: {ric_text}\n"
        f"Nextcloud: {db_user.nextcloud_url}\n"
        f"Timezone: {db_user.timezone}\n"
        f"Reminders: {db_user.lead_minutes} min x {db_user.repeat_count}\n"
        f"TX groups: {', '.join(parse_tx_groups(db_user.tx_group))}\n"
        f"Core: {SERVER_LABELS.get(db_user.dapnet_server, db_user.dapnet_server)}"
    )


@require_approved
async def timezone_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    if not context.args:
        await update.effective_message.reply_text(
            f"Current timezone: {user.timezone}\nUsage: /timezone Europe/Madrid"
        )
        return
    name = context.args[0]
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError:
        await update.effective_message.reply_text(
            "Unknown timezone. Example: Europe/Madrid"
        )
        return
    async with session_scope(session_factory_of(context)) as session:
        db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
        assert db_user is not None
        await repo.update_timezone(session, db_user, name)
    await update.effective_message.reply_text(f"Timezone updated to {name}.")


@require_approved
async def test_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    dapnet: DapnetClient = context.application.bot_data["dapnet"]
    text = format_test_message(user.dapnet_callsign)
    destinations = destination_callsigns(user)
    try:
        await dapnet.send_call(
            text,
            destinations,
            user.tx_group,
            server=user.dapnet_server,
        )
    except DapnetError as exc:
        await update.effective_message.reply_text(f"DAPNET rejected the test page: {exc}")
        return
    dest = ", ".join(name.upper() for name in destinations)
    await update.effective_message.reply_text(
        f"Test page sent to {dest} "
        f"({SERVER_LABELS.get(user.dapnet_server, user.dapnet_server)}): {text}"
    )


async def setup_commands(application: Application) -> None:
    await application.bot.set_my_commands(
        USER_BOT_COMMANDS, scope=BotCommandScopeDefault()
    )
    settings = application.bot_data["settings"]
    admin_commands = [*USER_BOT_COMMANDS, *ADMIN_BOT_COMMANDS]
    for admin_id in settings.admin_ids:
        try:
            await application.bot.set_my_commands(
                admin_commands, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception:
            logger.warning("Could not set admin command menu for %s", admin_id)


def register_handlers(application: Application) -> None:
    application.add_handler(build_register_handler())
    application.add_handler(build_rics_handler())
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("calendars", calendars_command))
    application.add_handler(CommandHandler("reminders", reminders_command))
    application.add_handler(CommandHandler("txgroup", txgroup_command))
    application.add_handler(CommandHandler("server", server_command))
    application.add_handler(CommandHandler("rics", rics_command))
    application.add_handler(CommandHandler("timezone", timezone_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("refresh", refresh_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin:"))
    application.add_handler(CallbackQueryHandler(calendars_callback, pattern=r"^cal:"))
    application.add_handler(CallbackQueryHandler(reminders_callback, pattern=r"^rem:"))
    application.add_handler(CallbackQueryHandler(txgroup_callback, pattern=r"^txg:"))
    application.add_handler(CallbackQueryHandler(server_callback, pattern=r"^srv:"))
    application.add_handler(CallbackQueryHandler(rics_callback, pattern=r"^ric:(toggle|del|self):"))
    application.add_handler(CallbackQueryHandler(delete_callback, pattern=r"^del:"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help:"))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
