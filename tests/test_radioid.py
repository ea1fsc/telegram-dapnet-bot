from telegram_dapnet_bot.services.radioid import process_dmr_id


def test_process_dmr_id_in_pocsag_range() -> None:
    assert process_dmr_id(2141234) == 141234
    assert process_dmr_id(145904) == 145904


def test_process_dmr_id_rejects_invalid() -> None:
    assert process_dmr_id(0) == 0
    assert process_dmr_id(-3) == 0
