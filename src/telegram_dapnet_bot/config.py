from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from telegram_dapnet_bot.services.txgroups import normalize_server


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    admin_telegram_ids: str

    dapnet_api_url: str = "https://hampager.de/api"
    dapnet_api_url_es: str = "http://dapnet.es:8080"
    dapnet_callsign: str
    dapnet_password: str
    dapnet_default_tx_group: str = "all"
    dapnet_default_server: str = "de"

    encryption_key: str

    database_url: str = "sqlite+aiosqlite:///./data/bot.db"

    sync_interval_seconds: int = 600
    dispatch_interval_seconds: int = 60
    fetch_event_window_days: int = 14
    misfire_grace_minutes: int = 30

    default_timezone: str = "Europe/Madrid"
    default_lead_minutes: int = 60
    default_repeat_count: int = 1

    log_level: str = "INFO"

    caldav_ssl_verify: bool = True
    caldav_ca_bundle: str = ""

    @field_validator("dapnet_api_url", "dapnet_api_url_es")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("dapnet_default_server")
    @classmethod
    def normalize_default_server(cls, value: str) -> str:
        return normalize_server(value)

    @field_validator("caldav_ca_bundle")
    @classmethod
    def validate_ca_bundle(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned and not Path(cleaned).is_file():
            raise ValueError(f"CALDAV_CA_BUNDLE is not a file: {cleaned}")
        return cleaned

    @property
    def admin_ids(self) -> frozenset[int]:
        return frozenset(
            int(part.strip())
            for part in self.admin_telegram_ids.split(",")
            if part.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
