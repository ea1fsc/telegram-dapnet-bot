from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from telegram_dapnet_bot.bot.access import load_user, session_factory_of
from telegram_dapnet_bot.bot.keyboards import delete_confirm_keyboard
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.session import session_scope

DELETE_CONFIRM_TEXT = (
    "This will permanently erase your account from this bot:\n"
    "- Nextcloud URL, username and app password\n"
    "- calendars, cached events and reminder history\n"
    "- DAPNET callsign and preferences\n\n"
    "You can /register again later.\n\n"
    "Tap a button or send /delete confirm."
)


async def _erase_user(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> bool:
    async with session_scope(session_factory_of(context)) as session:
        db_user = await repo.get_user_by_telegram_id(session, telegram_id)
        if db_user is None:
            return False
        await repo.delete_user(session, db_user)
        return True


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    db_user = await load_user(context, user.id)
    if db_user is None:
        await message.reply_text("You have no data stored here.")
        return
    args = [part.lower() for part in (context.args or [])]
    if args and args[0] == "confirm":
        deleted = await _erase_user(context, user.id)
        if deleted:
            await message.reply_text(
                "Your data has been deleted. Use /register if you want to come back."
            )
        else:
            await message.reply_text("You have no data stored here.")
        return
    await message.reply_text(
        DELETE_CONFIRM_TEXT,
        reply_markup=delete_confirm_keyboard(),
    )


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg_user = update.effective_user
    if query is None or tg_user is None:
        return
    await query.answer()
    data = query.data or ""
    if data == "del:cancel":
        await query.edit_message_text("Account deletion cancelled.")
        return
    if data != "del:confirm":
        return
    deleted = await _erase_user(context, tg_user.id)
    if deleted:
        await query.edit_message_text(
            "Your data has been deleted. Use /register if you want to come back."
        )
        return
    await query.edit_message_text("You have no data stored here.")
