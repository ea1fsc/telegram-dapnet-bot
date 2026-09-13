from telegram_dapnet_bot.bot.help_menu import build_help, help_keyboard
from telegram_dapnet_bot.db.models import UserStatus


def _callback_data(markup) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    }


def test_help_unregistered_offers_register() -> None:
    text, markup = build_help(None, is_admin=False)
    assert "You are not registered yet." in text
    assert "/register" in text
    assert "/calendars" not in text
    assert _callback_data(markup) == {"help:register", "help:status"}


def test_help_pending_has_status_and_delete() -> None:
    text, markup = build_help(UserStatus.PENDING, is_admin=False)
    assert "waiting for an administrator" in text
    data = _callback_data(markup)
    assert data == {"help:status", "help:register", "help:delete"}
    assert "help:calendars" not in data


def test_help_rejected_can_register_again() -> None:
    text, markup = build_help(UserStatus.REJECTED, is_admin=False)
    assert "rejected" in text.lower()
    data = _callback_data(markup)
    assert "help:register" in data
    assert "help:delete" in data
    assert "help:test" not in data


def test_help_approved_includes_refresh_and_delete() -> None:
    text, markup = build_help(UserStatus.APPROVED, is_admin=False)
    assert "/refresh" in text
    assert "/delete" in text
    assert "/rics" in text
    assert "Telegram" in text
    data = _callback_data(markup)
    assert {
        "help:status",
        "help:calendars",
        "help:reminders",
        "help:txgroup",
        "help:server",
        "help:rics",
        "help:timezone",
        "help:test",
        "help:refresh",
        "help:delete",
    } <= data
    assert "help:pending" not in data


def test_help_non_admin_hides_admin_commands() -> None:
    text, markup = build_help(UserStatus.APPROVED, is_admin=False)
    assert "/pending" not in text
    assert "/approve" not in text
    assert "help:pending" not in _callback_data(markup)


def test_help_admin_adds_pending_even_if_unregistered() -> None:
    text, markup = build_help(None, is_admin=True)
    assert "/pending" in text
    data = _callback_data(markup)
    assert "help:pending" in data
    assert "help:users" in data
    keyboard = help_keyboard(UserStatus.APPROVED, is_admin=True)
    assert "help:pending" in _callback_data(keyboard)


def test_botfather_admin_commands_are_not_in_user_menu() -> None:
    from telegram_dapnet_bot.bot.handlers import ADMIN_BOT_COMMANDS, USER_BOT_COMMANDS

    user_names = {command.command for command in USER_BOT_COMMANDS}
    admin_names = {command.command for command in ADMIN_BOT_COMMANDS}
    assert admin_names.isdisjoint(user_names)
    assert {"pending", "users", "approve", "reject"} == admin_names
    assert "rics" in user_names
