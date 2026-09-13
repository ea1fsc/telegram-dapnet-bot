from __future__ import annotations

from dataclasses import dataclass

from telegram_dapnet_bot.db.models import User, UserRic
from telegram_dapnet_bot.services.radioid import process_dmr_id


@dataclass
class RicChoice:
    ric: int
    callsign: str
    source: str = "manual"
    selected: bool = False


def parse_ric_input(text: str) -> int:
    cleaned = (text or "").strip().replace(",", "").replace(" ", "")
    if not cleaned.isdigit():
        return 0
    return process_dmr_id(int(cleaned))


def unique_callsigns(*groups: list[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            name = (raw or "").strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


def destination_callsigns(user: User) -> list[str]:
    rows = list(user.rics or [])
    if not rows:
        return unique_callsigns([user.dapnet_callsign])
    return unique_callsigns(
        [item.callsign for item in rows if item.enabled and item.callsign]
    )


def format_ric_label(ric: int, callsign: str, *, enabled: bool | None = None) -> str:
    name = (callsign or "").upper() or "?"
    text = f"{ric} ({name})"
    if enabled is None:
        return text
    mark = "ON" if enabled else "OFF"
    return f"{mark} · {text}"


def serialize_rics(items: list[UserRic] | list[RicChoice]) -> str:
    return ",".join(str(item.ric) for item in items)
