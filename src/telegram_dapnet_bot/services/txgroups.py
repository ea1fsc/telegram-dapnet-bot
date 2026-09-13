import re

TX_GROUP_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
PRESET_TX_GROUPS = ("all", "ea-all", "dl-all", "us-all")
SERVER_DE = "de"
SERVER_ES = "es"
SERVER_LABELS = {
    SERVER_ES: "Spain (dapnet.es)",
    SERVER_DE: "Germany (hampager.de)",
}


def filter_tx_groups(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    parts = raw if isinstance(raw, list) else raw.split(",")
    groups: list[str] = []
    seen: set[str] = set()
    for part in parts:
        name = part.strip().lower()
        if not name or name in seen or not TX_GROUP_RE.match(name):
            continue
        seen.add(name)
        groups.append(name)
    return groups


def parse_tx_groups(raw: str | list[str] | None) -> list[str]:
    return filter_tx_groups(raw) or ["all"]


def join_tx_groups(groups: list[str]) -> str:
    cleaned = parse_tx_groups(groups)
    return ",".join(cleaned)


def toggle_tx_group(current: str, group: str) -> str:
    groups = parse_tx_groups(current)
    name = group.strip().lower()
    if not TX_GROUP_RE.match(name):
        return join_tx_groups(groups)
    if name in groups:
        groups = [item for item in groups if item != name]
    else:
        groups.append(name)
    return join_tx_groups(groups)


def normalize_server(value: str | None) -> str:
    if (value or "").lower() in {SERVER_ES, "ea", "es", "1", "spain"}:
        return SERVER_ES
    return SERVER_DE
