from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_dapnet_bot.db.models import Calendar
from telegram_dapnet_bot.services.txgroups import (
    PRESET_TX_GROUPS,
    SERVER_DE,
    SERVER_ES,
    SERVER_LABELS,
    parse_tx_groups,
)

LEAD_CHOICES = (
    (15, "15 min"),
    (30, "30 min"),
    (60, "1 hour"),
    (180, "3 hours"),
    (1440, "1 day"),
    (10080, "1 week"),
)

REPEAT_CHOICES = (1, 2, 3)


def admin_review_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Approve", callback_data=f"admin:approve:{telegram_id}"
                ),
                InlineKeyboardButton(
                    "Reject", callback_data=f"admin:reject:{telegram_id}"
                ),
            ]
        ]
    )


def calendars_keyboard(calendars: list[Calendar]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{'ON' if calendar.enabled else 'OFF'} · {calendar.name}",
                callback_data=f"cal:toggle:{calendar.id}",
            )
        ]
        for calendar in calendars
    ]
    rows.append(
        [
            InlineKeyboardButton("Refresh list", callback_data="cal:refresh"),
            InlineKeyboardButton("Refresh events", callback_data="cal:events"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Delete my data", callback_data="del:confirm"),
                InlineKeyboardButton("Cancel", callback_data="del:cancel"),
            ]
        ]
    )


def reminders_keyboard(lead_minutes: int, repeat_count: int) -> InlineKeyboardMarkup:
    lead_row = [
        InlineKeyboardButton(
            f"{'• ' if minutes == lead_minutes else ''}{label}",
            callback_data=f"rem:lead:{minutes}",
        )
        for minutes, label in LEAD_CHOICES
    ]
    count_row = [
        InlineKeyboardButton(
            f"{'• ' if count == repeat_count else ''}{count}×",
            callback_data=f"rem:count:{count}",
        )
        for count in REPEAT_CHOICES
    ]
    return InlineKeyboardMarkup([lead_row[:3], lead_row[3:], count_row])


def server_keyboard(selected: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{'• ' if selected == SERVER_ES else ''}{SERVER_LABELS[SERVER_ES]}",
                    callback_data=f"srv:{SERVER_ES}",
                )
            ],
            [
                InlineKeyboardButton(
                    f"{'• ' if selected == SERVER_DE else ''}{SERVER_LABELS[SERVER_DE]}",
                    callback_data=f"srv:{SERVER_DE}",
                )
            ],
        ]
    )


def register_server_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    SERVER_LABELS[SERVER_ES], callback_data=f"reg:server:{SERVER_ES}"
                )
            ],
            [
                InlineKeyboardButton(
                    SERVER_LABELS[SERVER_DE], callback_data=f"reg:server:{SERVER_DE}"
                )
            ],
        ]
    )


def txgroup_keyboard(
    current: str, catalog: list[str] | None = None
) -> InlineKeyboardMarkup:
    selected = set(parse_tx_groups(current))
    names: list[str] = []
    for name in (*PRESET_TX_GROUPS, *(catalog or []), *parse_tx_groups(current)):
        if name not in names:
            names.append(name)
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for name in names[:18]:
        mark = "ON" if name in selected else "OFF"
        row.append(
            InlineKeyboardButton(
                f"{mark} {name}", callback_data=f"txg:toggle:{name}"
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [InlineKeyboardButton("Refresh DAPNET groups", callback_data="txg:refresh")]
    )
    return InlineKeyboardMarkup(rows)


def register_rics_keyboard(
    choices: list[tuple[int, str, bool]],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ric, callsign, selected in choices[:12]:
        mark = "ON" if selected else "OFF"
        label = f"{mark} · {ric} ({callsign.upper()})"
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"reg:ric:toggle:{ric}")]
        )
    rows.append(
        [InlineKeyboardButton("Enter RIC manually", callback_data="reg:ric:manual")]
    )
    rows.append([InlineKeyboardButton("Done", callback_data="reg:ric:done")])
    return InlineKeyboardMarkup(rows)


def ric_label_keyboard(ric: int, own_callsign: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"Use {own_callsign.upper()}",
                    callback_data=f"reg:ric:self:{ric}",
                )
            ]
        ]
    )


def rics_keyboard(rows_data: list[tuple[int, int, str, bool]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for row_id, ric, callsign, enabled in rows_data[:12]:
        mark = "ON" if enabled else "OFF"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{mark} · {ric} ({callsign.upper()})",
                    callback_data=f"ric:toggle:{row_id}",
                ),
                InlineKeyboardButton("Remove", callback_data=f"ric:del:{row_id}"),
            ]
        )
    rows.append([InlineKeyboardButton("Add RIC", callback_data="ric:add")])
    return InlineKeyboardMarkup(rows)


def rics_own_callsign_keyboard(ric: int, own_callsign: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"Use {own_callsign.upper()}",
                    callback_data=f"ric:self:{ric}",
                )
            ]
        ]
    )
