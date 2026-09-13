from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from telegram_dapnet_bot.bot.access import require_approved, session_factory_of
from telegram_dapnet_bot.bot.keyboards import rics_keyboard, rics_own_callsign_keyboard
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import User, UserStatus
from telegram_dapnet_bot.db.session import session_scope
from telegram_dapnet_bot.services.rics import format_ric_label, parse_ric_input

logger = logging.getLogger(__name__)

CALLSIGN_RE = re.compile(r"^[a-z0-9/]{3,20}$")
ASK_NUMBER, ASK_LABEL = range(2)
RICS_TIMEOUT_SECONDS = 600


def _menu_text(rows) -> str:
    if not rows:
        return (
            "No RICs yet. Calendar pages go to your DAPNET callsign until you add one.\n"
            "Tap Add RIC, send /rics 145904, or /rics 145904 CALLSIGN for a new one."
        )
    lines = [
        format_ric_label(row.ric, row.callsign, enabled=row.enabled) for row in rows
    ]
    return (
        "RICs that receive your calendar pages.\n"
        "ON = send to that pager's DAPNET callsign. "
        "DAPNET delivers to every pager of that callsign.\n\n"
        + "\n".join(lines)
        + "\n\nTap to enable or disable, or send /rics 145904 CALLSIGN"
    )


def _markup(rows) -> object:
    return rics_keyboard(
        [(row.id, row.ric, row.callsign, row.enabled) for row in rows]
    )


async def _load_rows(context: ContextTypes.DEFAULT_TYPE, telegram_id: int):
    async with session_scope(session_factory_of(context)) as session:
        user = await repo.get_user_by_telegram_id(session, telegram_id)
        if user is None:
            return None, []
        rows = await repo.list_user_rics(session, user.id)
        return user, rows


@require_approved
async def rics_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    args = list(context.args or [])
    if args:
        await _rics_from_args(update, context, user, args)
        return
    _user, rows = await _load_rows(context, user.telegram_id)
    await update.effective_message.reply_text(
        _menu_text(rows),
        reply_markup=_markup(rows),
    )


async def _rics_from_args(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: User,
    args: list[str],
) -> None:
    assert update.effective_message is not None
    action = args[0].lower()
    rest = args[1:]
    if action == "remove" and rest:
        ric = parse_ric_input(rest[0])
        if ric <= 0:
            await update.effective_message.reply_text("That RIC number is not valid.")
            return
        async with session_scope(session_factory_of(context)) as session:
            db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
            assert db_user is not None
            rows = await repo.list_user_rics(session, db_user.id)
            match = next((row for row in rows if row.ric == ric), None)
            if match is None:
                await update.effective_message.reply_text(f"RIC {ric} is not in your list.")
                return
            await repo.remove_user_ric(session, db_user, match)
            rows = await repo.list_user_rics(session, db_user.id)
        await update.effective_message.reply_text(
            f"Removed RIC {ric}.\n\n" + _menu_text(rows),
            reply_markup=_markup(rows),
        )
        return
    if action in {"add", "remove"}:
        tokens = rest
    else:
        tokens = args
    if not tokens:
        await update.effective_message.reply_text(
            "Usage: /rics 145904 or /rics 145904 ea1abc or /rics remove 145904"
        )
        return
    ric = parse_ric_input(tokens[0])
    if ric <= 0:
        await update.effective_message.reply_text("That RIC number is not valid.")
        return
    label = tokens[1].strip().lower() if len(tokens) > 1 else None
    if label and not CALLSIGN_RE.match(label):
        await update.effective_message.reply_text(
            "That callsign does not look valid. Use letters and numbers only (3-20)."
        )
        return
    added, needed_label = await _try_add_ric(context, user, ric, label)
    if needed_label:
        context.user_data["rics_pending"] = ric
        await update.effective_message.reply_text(
            f"RIC {ric} is not in the catalog yet.\n"
            f"Send /rics {ric} CALLSIGN, or tap the button to use yours.",
            reply_markup=rics_own_callsign_keyboard(ric, user.dapnet_callsign),
        )
        return
    _user, rows = await _load_rows(context, user.telegram_id)
    await update.effective_message.reply_text(
        f"Added RIC {added}.\n\n" + _menu_text(rows),
        reply_markup=_markup(rows),
    )


async def _try_add_ric(
    context: ContextTypes.DEFAULT_TYPE,
    user: User,
    ric: int,
    label: str | None,
) -> tuple[str, bool]:
    async with session_scope(session_factory_of(context)) as session:
        db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
        assert db_user is not None
        catalog = await repo.get_catalog_ric(session, ric)
        callsign = label or (catalog.callsign if catalog else None)
        if not callsign:
            return "", True
        source = "catalog" if catalog and not label else "manual"
        row = await repo.add_user_ric(
            session, db_user, ric, callsign, source=source, enabled=True
        )
        return format_ric_label(row.ric, row.callsign), False


async def rics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        if data.startswith("ric:self:"):
            ric = int(data.rsplit(":", 1)[-1])
            await repo.add_user_ric(
                session,
                user,
                ric,
                user.dapnet_callsign,
                source="manual",
                enabled=True,
            )
            context.user_data.pop("rics_pending", None)
        elif data.startswith("ric:toggle:"):
            row = await repo.get_user_ric(session, int(data.rsplit(":", 1)[-1]))
            if row is None or row.user_id != user.id:
                await query.edit_message_text("RIC not found.")
                return
            await repo.toggle_user_ric(session, row)
        elif data.startswith("ric:del:"):
            row = await repo.get_user_ric(session, int(data.rsplit(":", 1)[-1]))
            if row is None or row.user_id != user.id:
                await query.edit_message_text("RIC not found.")
                return
            await repo.remove_user_ric(session, user, row)
        else:
            return
        rows = await repo.list_user_rics(session, user.id)
    await query.edit_message_text(_menu_text(rows), reply_markup=_markup(rows))


async def rics_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END
    await query.answer()
    tg_user = update.effective_user
    if tg_user is None:
        return ConversationHandler.END
    async with session_scope(session_factory_of(context)) as session:
        user = await repo.get_user_by_telegram_id(session, tg_user.id)
        if user is None or user.status != UserStatus.APPROVED:
            await query.edit_message_text("You need an approved account.")
            return ConversationHandler.END
    await query.edit_message_text(
        "Send the RIC number. If it already exists in this bot or on DAPNET, "
        "I will reuse its callsign. /cancel to abort."
    )
    return ASK_NUMBER


async def rics_receive_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.effective_message is not None
    user = update.effective_user
    if user is None:
        return ConversationHandler.END
    ric = parse_ric_input(update.effective_message.text or "")
    if ric <= 0:
        await update.effective_message.reply_text(
            "That is not a valid RIC. Send digits only."
        )
        return ASK_NUMBER
    db_user = await _approved_user(context, user.id)
    if db_user is None:
        await update.effective_message.reply_text("You need an approved account.")
        return ConversationHandler.END
    added, needed_label = await _try_add_ric(context, db_user, ric, None)
    if needed_label:
        context.user_data["rics_pending"] = ric
        await update.effective_message.reply_text(
            f"RIC {ric} is not in the catalog yet.\n"
            "Send the DAPNET callsign that owns this pager, "
            "or tap the button to use yours.",
            reply_markup=rics_own_callsign_keyboard(ric, db_user.dapnet_callsign),
        )
        return ASK_LABEL
    _user, rows = await _load_rows(context, user.id)
    await update.effective_message.reply_text(
        f"Added RIC {added}.\n\n" + _menu_text(rows),
        reply_markup=_markup(rows),
    )
    return ConversationHandler.END


async def rics_receive_label(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.effective_message is not None
    user = update.effective_user
    if user is None:
        return ConversationHandler.END
    label = (update.effective_message.text or "").strip().lower()
    if not CALLSIGN_RE.match(label):
        await update.effective_message.reply_text(
            "That callsign does not look valid. Use letters and numbers only (3-20)."
        )
        return ASK_LABEL
    pending = context.user_data.get("rics_pending")
    if not pending:
        await update.effective_message.reply_text("Send a RIC number first.")
        return ConversationHandler.END
    db_user = await _approved_user(context, user.id)
    if db_user is None:
        return ConversationHandler.END
    added, _needed = await _try_add_ric(context, db_user, int(pending), label)
    context.user_data.pop("rics_pending", None)
    _user, rows = await _load_rows(context, user.id)
    await update.effective_message.reply_text(
        f"Added RIC {added}.\n\n" + _menu_text(rows),
        reply_markup=_markup(rows),
    )
    return ConversationHandler.END


async def rics_label_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    tg_user = update.effective_user
    if query is None or tg_user is None:
        return ConversationHandler.END
    await query.answer()
    ric = int((query.data or "0").rsplit(":", 1)[-1])
    db_user = await _approved_user(context, tg_user.id)
    if db_user is None:
        await query.edit_message_text("You need an approved account.")
        return ConversationHandler.END
    added, _needed = await _try_add_ric(context, db_user, ric, db_user.dapnet_callsign)
    context.user_data.pop("rics_pending", None)
    _user, rows = await _load_rows(context, tg_user.id)
    await query.edit_message_text(
        f"Added RIC {added}.\n\n" + _menu_text(rows),
        reply_markup=_markup(rows),
    )
    return ConversationHandler.END


async def rics_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("rics_pending", None)
    if update.effective_message:
        await update.effective_message.reply_text("Cancelled.")
    return ConversationHandler.END


async def _approved_user(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> User | None:
    async with session_scope(session_factory_of(context)) as session:
        user = await repo.get_user_by_telegram_id(session, telegram_id)
        if user is None or user.status != UserStatus.APPROVED:
            return None
        return user


def build_rics_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(rics_add_start, pattern=r"^ric:add$")],
        states={
            ASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rics_receive_number)
            ],
            ASK_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rics_receive_label),
                CallbackQueryHandler(rics_label_self, pattern=r"^ric:self:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", rics_cancel)],
        conversation_timeout=RICS_TIMEOUT_SECONDS,
    )
