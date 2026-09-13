from types import SimpleNamespace

from telegram_dapnet_bot.services.rics import (
    destination_callsigns,
    parse_ric_input,
    serialize_rics,
)


def test_parse_ric_input_strips_and_maps_dmr() -> None:
    assert parse_ric_input("145904") == 145904
    assert parse_ric_input(" 2,141,234 ") == 141234
    assert parse_ric_input("abc") == 0


def test_destination_callsigns_fallback_without_rics() -> None:
    user = SimpleNamespace(dapnet_callsign="ea1abc", rics=[])
    assert destination_callsigns(user) == ["ea1abc"]


def test_destination_callsigns_uses_enabled_only() -> None:
    user = SimpleNamespace(
        dapnet_callsign="ea1abc",
        rics=[
            SimpleNamespace(callsign="ea1abc", enabled=True),
            SimpleNamespace(callsign="ea4hqf", enabled=True),
            SimpleNamespace(callsign="ea9zzz", enabled=False),
            SimpleNamespace(callsign="ea1abc", enabled=True),
        ],
    )
    assert destination_callsigns(user) == ["ea1abc", "ea4hqf"]


def test_destination_callsigns_empty_when_all_disabled() -> None:
    user = SimpleNamespace(
        dapnet_callsign="ea1abc",
        rics=[SimpleNamespace(callsign="ea1abc", enabled=False)],
    )
    assert destination_callsigns(user) == []


def test_serialize_rics() -> None:
    assert serialize_rics([SimpleNamespace(ric=145904)]) == "145904"
