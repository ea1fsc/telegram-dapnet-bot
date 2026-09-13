from telegram_dapnet_bot.services.dapnet import SubscriberCheck, parse_pager_rics


def test_subscriber_requires_user_and_callsign() -> None:
    assert not SubscriberCheck(
        exists_user=False, exists_callsign=True, pager_count=1, pagers_visible=True
    ).ok
    assert not SubscriberCheck(
        exists_user=True, exists_callsign=False, pager_count=1, pagers_visible=True
    ).ok


def test_hidden_pagers_accept_existing_callsign() -> None:
    assert SubscriberCheck(
        exists_user=True, exists_callsign=True, pager_count=None, pagers_visible=False
    ).ok


def test_visible_pagers_require_at_least_one() -> None:
    assert not SubscriberCheck(
        exists_user=True, exists_callsign=True, pager_count=0, pagers_visible=True
    ).ok
    assert SubscriberCheck(
        exists_user=True, exists_callsign=True, pager_count=2, pagers_visible=True
    ).ok


def test_parse_pager_rics_from_dapnet_payload() -> None:
    assert parse_pager_rics(None) == []
    assert parse_pager_rics({"name": "ea1abc"}) == []
    assert parse_pager_rics({"pagers": [145904, {"number": 2080905}]}) == [
        145904,
        2080905,
    ]
    assert parse_pager_rics({"pagers": [2_141_234]}) == [141234]
