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

from telegram_dapnet_bot.bot.access import session_factory_of
from telegram_dapnet_bot.bot.keyboards import (
    admin_review_keyboard,
    register_rics_keyboard,
    register_server_keyboard,
    ric_label_keyboard,
)
from telegram_dapnet_bot.crypto import SecretBox
from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import UserStatus
from telegram_dapnet_bot.db.session import session_scope
from telegram_dapnet_bot.services.dapnet import DapnetClient, DapnetError, parse_pager_rics
from telegram_dapnet_bot.services.nextcloud import (
    NextcloudError,
    normalize_caldav_url,
    probe_connection,
)
from telegram_dapnet_bot.services.radioid import lookup_rics
from telegram_dapnet_bot.services.rics import (
    RicChoice,
    parse_ric_input,
    serialize_rics,
)
from telegram_dapnet_bot.services.txgroups import SERVER_LABELS, normalize_server

logger = logging.getLogger(__name__)

(
    ASK_CALLSIGN,
    ASK_SERVER,
    ASK_RICS,
    ASK_RIC_CALLSIGN,
    ASK_URL,
    ASK_NC_USER,
    ASK_PASSWORD,
) = range(7)
CALLSIGN_RE = re.compile(r"^[a-z0-9/]{3,20}$")
REGISTER_TIMEOUT_SECONDS = 600


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query is not None:
        await update.callback_query.answer()
    assert update.effective_message is not None
    await update.effective_message.reply_text(
        "Let's register your account.\n\n"
        "1) DAPNET callsign (the subscriber must have at least one RIC).\n"
        "2) Choose which RICs should receive calendar pages.\n"
        "3) Your Nextcloud URL, username and app password.\n\n"
        "Send your callsign or /cancel to abort."
    )
    return ASK_CALLSIGN


async def receive_callsign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_message is not None
    callsign = (update.effective_message.text or "").strip().lower()
    if not CALLSIGN_RE.match(callsign):
        await update.effective_message.reply_text(
            "That callsign does not look valid. Use letters and numbers only (3-20)."
        )
        return ASK_CALLSIGN

    dapnet: DapnetClient = context.application.bot_data["dapnet"]
    try:
        check = await dapnet.check_subscriber(callsign)
    except DapnetError:
        logger.exception("DAPNET validation failed")
        await update.effective_message.reply_text(
            "I could not query DAPNET right now. Please try again later."
        )
        return ConversationHandler.END

    if not check.exists_user:
        await update.effective_message.reply_text(
            "That callsign is not a registered DAPNET user."
        )
        return ASK_CALLSIGN
    if not check.exists_callsign:
        await update.effective_message.reply_text(
            "That callsign has no DAPNET subscriber. "
            "You need at least one RIC linked to it."
        )
        return ASK_CALLSIGN
    if check.pagers_visible and (check.pager_count or 0) < 1:
        await update.effective_message.reply_text(
            "The subscriber exists but has no RIC. "
            "Add a pager on hampager.de and try again."
        )
        return ASK_CALLSIGN

    context.user_data["reg_callsign"] = callsign
    await update.effective_message.reply_text(
        "Callsign looks good.\n"
        "Which DAPNET core should receive your pages?",
        reply_markup=register_server_keyboard(),
    )
    return ASK_SERVER


async def receive_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ASK_SERVER
    await query.answer()
    server = normalize_server((query.data or "").split(":")[-1])
    context.user_data["reg_server"] = server
    callsign = context.user_data.get("reg_callsign") or ""
    choices = await _suggest_rics(context, callsign)
    selected = {
        str(choice.ric): _choice_dict(choice)
        for choice in choices
        if choice.selected
    }
    context.user_data["reg_ric_choices"] = [_choice_dict(choice) for choice in choices]
    context.user_data["reg_rics_selected"] = selected
    await query.edit_message_text(
        _rics_prompt_text(callsign, selected),
        reply_markup=_rics_markup(choices, selected),
    )
    return ASK_RICS


async def receive_rics_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    if query is None:
        return ASK_RICS
    await query.answer()
    data = query.data or ""
    callsign = context.user_data.get("reg_callsign") or ""
    if data == "reg:ric:manual":
        await query.edit_message_text(
            "Send the RIC number (1-2097151). "
            "If that RIC already exists in DAPNET or in this bot, "
            "I will reuse its callsign."
        )
        return ASK_RICS
    if data == "reg:ric:done":
        selected = _selected_map(context)
        if not selected:
            await query.edit_message_text(
                "Select at least one RIC, or send a RIC number.\n\n"
                + _rics_prompt_text(callsign, selected),
                reply_markup=_current_rics_markup(context),
            )
            return ASK_RICS
        await query.edit_message_text(
            f"RICs: {_format_selected(selected)}.\n"
            "Now send your Nextcloud URL (for example https://cloud.example.org)."
        )
        return ASK_URL
    if data.startswith("reg:ric:toggle:"):
        try:
            ric = int(data.rsplit(":", 1)[-1])
        except ValueError:
            return ASK_RICS
        selected = _selected_map(context)
        if str(ric) in selected:
            selected.pop(str(ric), None)
        else:
            choice = _choice_by_ric(context, ric)
            if choice is None:
                return ASK_RICS
            selected[str(ric)] = choice
        context.user_data["reg_rics_selected"] = selected
        await query.edit_message_text(
            _rics_prompt_text(callsign, selected),
            reply_markup=_current_rics_markup(context),
        )
        return ASK_RICS
    return ASK_RICS


async def receive_rics_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.effective_message is not None
    ric = parse_ric_input(update.effective_message.text or "")
    if ric <= 0:
        await update.effective_message.reply_text(
            "That is not a valid RIC. Send digits only, or tap a button."
        )
        return ASK_RICS
    return await _add_or_ask_label(update, context, ric)


async def receive_ric_label_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    if query is None:
        return ASK_RIC_CALLSIGN
    await query.answer()
    callsign = context.user_data.get("reg_callsign") or ""
    pending = context.user_data.get("reg_pending_ric")
    if not pending:
        await query.edit_message_text("I lost that RIC. Send the number again.")
        return ASK_RICS
    _select_ric(context, int(pending), callsign, "manual")
    context.user_data.pop("reg_pending_ric", None)
    selected = _selected_map(context)
    await query.edit_message_text(
        f"Added RIC {pending} ({callsign.upper()}).\n\n"
        + _rics_prompt_text(callsign, selected),
        reply_markup=_current_rics_markup(context),
    )
    return ASK_RICS


async def receive_ric_label_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.effective_message is not None
    label = (update.effective_message.text or "").strip().lower()
    pending = context.user_data.get("reg_pending_ric")
    if not pending:
        await update.effective_message.reply_text("Send a RIC number first.")
        return ASK_RICS
    if not CALLSIGN_RE.match(label):
        await update.effective_message.reply_text(
            "That callsign does not look valid. Use letters and numbers only (3-20)."
        )
        return ASK_RIC_CALLSIGN
    _select_ric(context, int(pending), label, "manual")
    context.user_data.pop("reg_pending_ric", None)
    callsign = context.user_data.get("reg_callsign") or ""
    selected = _selected_map(context)
    await update.effective_message.reply_text(
        f"Added RIC {pending} ({label.upper()}).\n\n"
        + _rics_prompt_text(callsign, selected),
        reply_markup=_current_rics_markup(context),
    )
    return ASK_RICS


async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_message is not None
    try:
        url = normalize_caldav_url(update.effective_message.text or "")
    except NextcloudError as exc:
        await update.effective_message.reply_text(str(exc))
        return ASK_URL
    context.user_data["reg_url"] = url
    await update.effective_message.reply_text("Nextcloud username:")
    return ASK_NC_USER


async def receive_nc_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_message is not None
    username = (update.effective_message.text or "").strip()
    if not username:
        await update.effective_message.reply_text("The username cannot be empty.")
        return ASK_NC_USER
    context.user_data["reg_nc_user"] = username
    await update.effective_message.reply_text(
        "Nextcloud app password (Settings → Security). "
        "I will delete this message when I receive it."
    )
    return ASK_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    user = update.effective_user
    assert message is not None and user is not None
    password = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        logger.debug("Could not delete password message")

    if not password:
        await message.reply_text("The app password cannot be empty.")
        return ASK_PASSWORD

    url = context.user_data["reg_url"]
    nc_user = context.user_data["reg_nc_user"]
    callsign = context.user_data["reg_callsign"]
    selected = list(_selected_map(context).values())
    dapnet_rics = serialize_rics(
        [RicChoice(int(item["ric"]), item["callsign"], item["source"]) for item in selected]
    )
    settings = context.application.bot_data["settings"]
    dapnet_server = context.user_data.get("reg_server") or settings.dapnet_default_server
    box: SecretBox = context.application.bot_data["secret_box"]

    try:
        calendars = await probe_connection(url, nc_user, password)
    except NextcloudError as exc:
        await message.reply_text(
            f"I could not connect to Nextcloud ({exc}). "
            "Check the URL, username and app password. You can /cancel or send another URL."
        )
        return ASK_URL

    async with session_scope(session_factory_of(context)) as session:
        existing = await repo.get_user_by_telegram_id(session, user.id)
        keep_approved = (
            existing is not None
            and existing.status == UserStatus.APPROVED
            and existing.dapnet_callsign == callsign
        )
        if keep_approved:
            status = UserStatus.APPROVED
        elif existing is not None and existing.status == UserStatus.APPROVED:
            status = UserStatus.PENDING
        else:
            status = UserStatus.PENDING

        db_user = await repo.upsert_user(
            session,
            telegram_id=user.id,
            telegram_username=user.username,
            dapnet_callsign=callsign,
            dapnet_rics=dapnet_rics,
            nextcloud_url=url,
            nextcloud_user=nc_user,
            nextcloud_password_encrypted=box.encrypt(password),
            timezone=(existing.timezone if existing else settings.default_timezone),
            tx_group=(existing.tx_group if existing else settings.dapnet_default_tx_group),
            dapnet_server=dapnet_server,
            lead_minutes=(
                existing.lead_minutes if existing else settings.default_lead_minutes
            ),
            repeat_count=(
                existing.repeat_count if existing else settings.default_repeat_count
            ),
            status=status,
        )
        await repo.replace_user_rics(
            session,
            db_user,
            [
                (int(item["ric"]), item["callsign"], item.get("source") or "manual")
                for item in selected
            ],
        )
        await repo.sync_calendar_catalog(
            session,
            db_user,
            [(item.name, item.url) for item in calendars],
        )

    if keep_approved:
        await message.reply_text(
            "Credentials updated. You remain approved.\n"
            "Choose calendars with /calendars. Manage RICs with /rics."
        )
        _clear_registration(context)
        return ConversationHandler.END

    await message.reply_text(
        "Registration submitted. An administrator must approve it before you "
        "can sync calendars. Check your status with /status."
    )
    await _notify_admins(
        context,
        user.id,
        user.username,
        callsign,
        dapnet_rics,
        dapnet_server,
        url,
        nc_user,
    )
    _clear_registration(context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear_registration(context)
    if update.effective_message:
        await update.effective_message.reply_text("Registration cancelled.")
    return ConversationHandler.END


def _choice_dict(choice: RicChoice) -> dict:
    return {
        "ric": choice.ric,
        "callsign": choice.callsign,
        "source": choice.source,
        "selected": choice.selected,
    }


def _selected_map(context: ContextTypes.DEFAULT_TYPE) -> dict[str, dict]:
    raw = context.user_data.get("reg_rics_selected") or {}
    return dict(raw)


def _choice_by_ric(context: ContextTypes.DEFAULT_TYPE, ric: int) -> dict | None:
    for item in context.user_data.get("reg_ric_choices") or []:
        if int(item["ric"]) == ric:
            return item
    selected = _selected_map(context).get(str(ric))
    return selected


def _select_ric(
    context: ContextTypes.DEFAULT_TYPE, ric: int, callsign: str, source: str
) -> None:
    item = {
        "ric": ric,
        "callsign": callsign.lower(),
        "source": source,
        "selected": True,
    }
    choices = list(context.user_data.get("reg_ric_choices") or [])
    if not any(int(row["ric"]) == ric for row in choices):
        choices.append(item)
        context.user_data["reg_ric_choices"] = choices
    selected = _selected_map(context)
    selected[str(ric)] = item
    context.user_data["reg_rics_selected"] = selected


def _format_selected(selected: dict[str, dict]) -> str:
    if not selected:
        return "(none)"
    parts = [
        f"{item['ric']} ({str(item['callsign']).upper()})"
        for item in selected.values()
    ]
    return ", ".join(parts)


def _rics_prompt_text(callsign: str, selected: dict[str, dict]) -> str:
    return (
        f"Core saved. Choose which RICs should receive pages for {callsign.upper()}.\n"
        "ON = I will send calendar pages to that pager's DAPNET callsign.\n"
        "You can tap RadioID/DAPNET matches, send a RIC number, or add one manually.\n"
        "If the RIC already exists in this bot, I reuse its callsign.\n\n"
        f"Selected: {_format_selected(selected)}"
    )


def _rics_markup(choices: list[RicChoice], selected: dict[str, dict]) -> object:
    rows = [
        (choice.ric, choice.callsign, str(choice.ric) in selected)
        for choice in choices
    ]
    return register_rics_keyboard(rows)


def _current_rics_markup(context: ContextTypes.DEFAULT_TYPE) -> object:
    selected = _selected_map(context)
    rows = []
    seen: set[int] = set()
    for item in context.user_data.get("reg_ric_choices") or []:
        ric = int(item["ric"])
        seen.add(ric)
        rows.append((ric, item["callsign"], str(ric) in selected))
    for key, item in selected.items():
        ric = int(item["ric"])
        if ric not in seen:
            rows.append((ric, item["callsign"], True))
    return register_rics_keyboard(rows)


async def _suggest_rics(
    context: ContextTypes.DEFAULT_TYPE, callsign: str
) -> list[RicChoice]:
    choices: list[RicChoice] = []
    radioid = await lookup_rics(callsign)
    for item in radioid:
        choices.append(
            RicChoice(item.ric, item.callsign.lower(), "radioid", selected=True)
        )
    dapnet: DapnetClient = context.application.bot_data["dapnet"]
    try:
        record = await dapnet.get_callsign(callsign)
        for ric in parse_pager_rics(record):
            if any(choice.ric == ric for choice in choices):
                continue
            choices.append(RicChoice(ric, callsign, "dapnet", selected=True))
    except DapnetError:
        logger.debug("Could not list DAPNET pagers for %s", callsign)
    return choices


async def _add_or_ask_label(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ric: int,
) -> int:
    message = update.effective_message
    assert message is not None
    callsign = context.user_data.get("reg_callsign") or ""
    catalog_callsign = None
    async with session_scope(session_factory_of(context)) as session:
        row = await repo.get_catalog_ric(session, ric)
        if row is not None:
            catalog_callsign = row.callsign
    source = "catalog" if catalog_callsign else "manual"
    label = catalog_callsign or _choice_by_ric(context, ric)
    if isinstance(label, dict):
        catalog_callsign = label.get("callsign")
        source = label.get("source") or source
    if catalog_callsign:
        _select_ric(context, ric, catalog_callsign, source)
        selected = _selected_map(context)
        note = (
            " from the existing catalog"
            if source == "catalog"
            else ""
        )
        await message.reply_text(
            f"Added RIC {ric} ({catalog_callsign.upper()}){note}.\n\n"
            + _rics_prompt_text(callsign, selected),
            reply_markup=_current_rics_markup(context),
        )
        return ASK_RICS
    context.user_data["reg_pending_ric"] = ric
    await message.reply_text(
        f"RIC {ric} is not in the catalog yet.\n"
        "Send the DAPNET callsign that owns this pager, "
        "or tap the button to use yours. Pages are sent to that callsign.",
        reply_markup=ric_label_keyboard(ric, callsign),
    )
    return ASK_RIC_CALLSIGN


def _clear_registration(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "reg_callsign",
        "reg_rics",
        "reg_server",
        "reg_url",
        "reg_nc_user",
        "reg_ric_choices",
        "reg_rics_selected",
        "reg_pending_ric",
    ):
        context.user_data.pop(key, None)


async def _notify_admins(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_id: int,
    username: str | None,
    callsign: str,
    rics: str,
    server: str,
    url: str,
    nc_user: str,
) -> None:
    settings = context.application.bot_data["settings"]
    handle = f"@{username}" if username else "(no username)"
    ric_line = rics or "no RIC selected"
    text = (
        "New registration request\n"
        f"Telegram: {handle} ({telegram_id})\n"
        f"Callsign: {callsign.upper()}\n"
        f"RIC: {ric_line}\n"
        f"Core: {SERVER_LABELS.get(server, server)}\n"
        f"Nextcloud: {url} ({nc_user})"
    )
    for admin_id in settings.admin_ids:
        try:
            await context.bot.send_message(
                admin_id,
                text,
                reply_markup=admin_review_keyboard(telegram_id),
            )
        except Exception:
            logger.exception("Could not notify admin %s", admin_id)


def build_register_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("register", register_start),
            CallbackQueryHandler(register_start, pattern=r"^help:register$"),
        ],
        states={
            ASK_CALLSIGN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_callsign)
            ],
            ASK_SERVER: [
                CallbackQueryHandler(receive_server, pattern=r"^reg:server:")
            ],
            ASK_RICS: [
                CallbackQueryHandler(receive_rics_callback, pattern=r"^reg:ric:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rics_number),
            ],
            ASK_RIC_CALLSIGN: [
                CallbackQueryHandler(
                    receive_ric_label_callback, pattern=r"^reg:ric:self:"
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ric_label_text),
            ],
            ASK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
            ASK_NC_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_nc_user)
            ],
            ASK_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=REGISTER_TIMEOUT_SECONDS,
    )
