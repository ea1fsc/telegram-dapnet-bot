from cryptography.fernet import Fernet

from telegram_dapnet_bot.crypto import SecretBox


def test_encrypt_roundtrip() -> None:
    box = SecretBox(Fernet.generate_key().decode())
    token = box.encrypt("app-password-secret")
    assert token != "app-password-secret"
    assert box.decrypt(token) == "app-password-secret"
