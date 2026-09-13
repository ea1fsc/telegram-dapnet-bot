from pathlib import Path

from telegram_dapnet_bot.services.nextcloud import (
    caldav_error_message,
    looks_like_tls_failure,
    ssl_verify_cert,
)


def test_ssl_verify_defaults_to_true() -> None:
    assert ssl_verify_cert() is True


def test_ssl_verify_can_be_disabled() -> None:
    assert ssl_verify_cert(verify=False) is False


def test_ssl_ca_bundle_is_merged_with_public_cas(tmp_path: Path) -> None:
    extra = tmp_path / "extra.pem"
    extra.write_text("-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")
    bundle = Path(ssl_verify_cert(ca_bundle=str(extra)))
    text = bundle.read_text(encoding="utf-8")
    assert "BEGIN CERTIFICATE" in text
    assert "MIIB" in text


def test_tls_failure_mentions_origin_ca() -> None:
    exc = Exception(
        "HTTPSConnectionPool(host='nc.example.org', port=443): Max retries exceeded "
        "(Caused by SSLError(SSLCertVerificationError(1, "
        "'[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed "
        "certificate')))"
    )
    assert looks_like_tls_failure(exc)
    message = caldav_error_message(exc, action="Could not read events")
    assert message.startswith("Could not read events: TLS certificate")
    assert "CALDAV_CA_BUNDLE" in message
    assert "cloudflare-origin-ca.pem" in message


def test_other_failures_keep_original_text() -> None:
    exc = Exception("401 Unauthorized")
    assert not looks_like_tls_failure(exc)
    assert (
        caldav_error_message(exc, action="Could not connect to Nextcloud")
        == "Could not connect to Nextcloud: 401 Unauthorized"
    )
