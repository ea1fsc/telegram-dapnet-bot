from telegram_dapnet_bot.services.txgroups import (
    SERVER_DE,
    SERVER_ES,
    filter_tx_groups,
    join_tx_groups,
    normalize_server,
    parse_tx_groups,
    toggle_tx_group,
)


def test_parse_defaults_to_all() -> None:
    assert parse_tx_groups("") == ["all"]
    assert parse_tx_groups(None) == ["all"]


def test_parse_comma_and_invalid() -> None:
    assert parse_tx_groups("ea-all, dl-all, NOPE!") == ["ea-all", "dl-all"]
    assert filter_tx_groups("???") == []


def test_toggle_adds_and_removes() -> None:
    current = toggle_tx_group("all", "ea-all")
    assert parse_tx_groups(current) == ["all", "ea-all"]
    current = toggle_tx_group(current, "all")
    assert parse_tx_groups(current) == ["ea-all"]


def test_join_and_server_aliases() -> None:
    assert join_tx_groups(["EA-ALL", "ea-all", "dl-all"]) == "ea-all,dl-all"
    assert normalize_server("ea") == SERVER_ES
    assert normalize_server("1") == SERVER_ES
    assert normalize_server("germany") == SERVER_DE
