from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from telegram_dapnet_bot.bot.access import require_approved, session_factory_of
from telegram_dapnet_bot.bot.keyboards import server_keyboard, txgroup_keyboard
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import User, UserStatus
from telegram_dapnet_bot.db.session import session_scope
from telegram_dapnet_bot.services.dapnet import DapnetClient, DapnetError
from telegram_dapnet_bot.services.txgroups import (
    SERVER_LABELS,
    filter_tx_groups,
    join_tx_groups,
    normalize_server,
    parse_tx_groups,
    toggle_tx_group,
)


def _txgroup_text(tx_group: str) -> str:
    groups = ", ".join(parse_tx_groups(tx_group))
    return (
        "DAPNET transmitter groups (spreads).\n"
        f"Active: {groups}\n\n"
        "Tap to enable or disable. "
        "You can also send /txgroup ea-all,dl-all"
    )


@require_approved
async def txgroup_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    if context.args:
        groups = filter_tx_groups(context.args if len(context.args) > 1 else context.args[0])
        if not groups:
            await update.effective_message.reply_text(
                "Invalid group. Use letters, numbers and hyphens: ea-all, dl-all"
            )
            return
        serialized = join_tx_groups(groups)
        async with session_scope(session_factory_of(context)) as session:
            db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
            assert db_user is not None
            await repo.update_tx_groups(session, db_user, serialized)
        await update.effective_message.reply_text(
            _txgroup_text(serialized),
            reply_markup=txgroup_keyboard(serialized),
        )
        return

    await update.effective_message.reply_text(
        _txgroup_text(user.tx_group),
        reply_markup=txgroup_keyboard(user.tx_group),
    )


async def txgroup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

        catalog: list[str] = []
        if data == "txg:refresh":
            dapnet: DapnetClient = context.application.bot_data["dapnet"]
            try:
                catalog = await dapnet.list_transmitter_groups(user.dapnet_server)
            except DapnetError:
                catalog = []
            current = user.tx_group
        elif data.startswith("txg:toggle:"):
            current = toggle_tx_group(user.tx_group, data.split(":", 2)[2])
            await repo.update_tx_groups(session, user, current)
        else:
            return

    await query.edit_message_text(
        _txgroup_text(current),
        reply_markup=txgroup_keyboard(current, catalog),
    )


@require_approved
async def server_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    assert update.effective_message is not None
    if context.args:
        server = normalize_server(context.args[0])
        async with session_scope(session_factory_of(context)) as session:
            db_user = await repo.get_user_by_telegram_id(session, user.telegram_id)
            assert db_user is not None
            await repo.update_dapnet_server(session, db_user, server)
        await update.effective_message.reply_text(
            f"DAPNET core: {SERVER_LABELS[server]}",
            reply_markup=server_keyboard(server),
        )
        return
    await update.effective_message.reply_text(
        f"Current DAPNET core: {SERVER_LABELS.get(user.dapnet_server, user.dapnet_server)}\n"
        "Choose which network should send your pages.",
        reply_markup=server_keyboard(user.dapnet_server),
    )


async def server_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg_user = update.effective_user
    if query is None or tg_user is None:
        return
    await query.answer()
    server = normalize_server((query.data or "").split(":", 1)[-1])
    async with session_scope(session_factory_of(context)) as session:
        user = await repo.get_user_by_telegram_id(session, tg_user.id)
        if user is None or user.status != UserStatus.APPROVED:
            await query.edit_message_text("You need an approved account.")
            return
        await repo.update_dapnet_server(session, user, server)
    await query.edit_message_text(
        f"DAPNET core: {SERVER_LABELS[server]}",
        reply_markup=server_keyboard(server),
    )
