from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_dapnet_bot.db.models import UserStatus

_COMMON_FOOTER = (
    "Tap a button or type the command in the chat. "
    "Messages from this bot never use Markdown."
)


def help_text(status: UserStatus | None, *, is_admin: bool = False) -> str:
    if status is None:
        body = (
            "This bot reads your Nextcloud calendars and pages you on DAPNET.\n"
            "An administrator must approve you. Your DAPNET callsign must exist "
            "and have a subscriber (RIC).\n\n"
            "You are not registered yet.\n\n"
            "Available commands:\n"
            "/register — sign up (callsign + Nextcloud)\n"
            "/status — your account status\n"
            "/help — this menu"
        )
    elif status == UserStatus.PENDING:
        body = (
            "Your registration is waiting for an administrator to approve it.\n\n"
            "Available commands:\n"
            "/status — your account status\n"
            "/register — submit again with new details\n"
            "/delete — erase all your data from this bot\n"
            "/cancel — abort an in-progress registration\n"
            "/help — this menu"
        )
    elif status == UserStatus.REJECTED:
        body = (
            "Your registration was rejected. You can register again.\n\n"
            "Available commands:\n"
            "/register — sign up again\n"
            "/status — your account status\n"
            "/delete — erase all your data from this bot\n"
            "/help — this menu"
        )
    else:
        body = (
            "Your account is approved. I send DAPNET pages and Telegram "
            "messages before each event.\n\n"
            "Available commands:\n"
            "/status — your account status\n"
            "/calendars — choose which calendars to sync\n"
            "/reminders — how early and how often to notify you\n"
            "/txgroup — DAPNET transmitter groups\n"
            "/server — Spain or Germany DAPNET core\n"
            "/rics — choose which RICs receive pages\n"
            "/timezone — timezone, e.g. /timezone Europe/Madrid\n"
            "/test — send a test DAPNET page\n"
            "/refresh — reload upcoming events from selected calendars\n"
            "/delete — erase all your data from this bot\n"
            "/help — this menu"
        )
    if is_admin:
        body += (
            "\n\nAdmin commands:\n"
            "/pending — waiting registrations\n"
            "/users — registered users\n"
            "/approve <telegram_id>\n"
            "/reject <telegram_id>"
        )
    return f"{body}\n\n{_COMMON_FOOTER}"


def help_keyboard(
    status: UserStatus | None, *, is_admin: bool = False
) -> InlineKeyboardMarkup:
    if status is None:
        rows = [
            [
                InlineKeyboardButton("Register", callback_data="help:register"),
                InlineKeyboardButton("Status", callback_data="help:status"),
            ]
        ]
    elif status == UserStatus.PENDING:
        rows = [
            [
                InlineKeyboardButton("Status", callback_data="help:status"),
                InlineKeyboardButton("Register again", callback_data="help:register"),
            ],
            [InlineKeyboardButton("Delete my data", callback_data="help:delete")],
        ]
    elif status == UserStatus.REJECTED:
        rows = [
            [
                InlineKeyboardButton("Register", callback_data="help:register"),
                InlineKeyboardButton("Status", callback_data="help:status"),
            ],
            [InlineKeyboardButton("Delete my data", callback_data="help:delete")],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("Status", callback_data="help:status"),
                InlineKeyboardButton("Calendars", callback_data="help:calendars"),
            ],
            [
                InlineKeyboardButton("Reminders", callback_data="help:reminders"),
                InlineKeyboardButton("TX groups", callback_data="help:txgroup"),
            ],
            [
                InlineKeyboardButton("DAPNET core", callback_data="help:server"),
                InlineKeyboardButton("RICs", callback_data="help:rics"),
            ],
            [
                InlineKeyboardButton("Timezone", callback_data="help:timezone"),
                InlineKeyboardButton("Test page", callback_data="help:test"),
            ],
            [
                InlineKeyboardButton("Refresh events", callback_data="help:refresh"),
                InlineKeyboardButton("Delete my data", callback_data="help:delete"),
            ],
        ]
    if is_admin:
        rows.append(
            [
                InlineKeyboardButton("Pending", callback_data="help:pending"),
                InlineKeyboardButton("Users", callback_data="help:users"),
            ]
        )
    return InlineKeyboardMarkup(rows)


def build_help(
    status: UserStatus | None, *, is_admin: bool = False
) -> tuple[str, InlineKeyboardMarkup]:
    return help_text(status, is_admin=is_admin), help_keyboard(status, is_admin=is_admin)
