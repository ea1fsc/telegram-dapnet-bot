from __future__ import annotations

import logging
from datetime import timedelta

from telegram.ext import Application

from telegram_dapnet_bot.bot.handlers import register_handlers, setup_commands
from telegram_dapnet_bot.config import Settings, get_settings
from telegram_dapnet_bot.crypto import SecretBox
from telegram_dapnet_bot.db.session import create_engine, create_session_factory, init_db
from telegram_dapnet_bot.services.dapnet import DapnetClient
from telegram_dapnet_bot.services.scheduler import dispatch_due_reminders, sync_all_users


def configure_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_application(settings: Settings) -> Application:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    secret_box = SecretBox(settings.encryption_key)
    dapnet = DapnetClient(
        {
            "de": settings.dapnet_api_url,
            "es": settings.dapnet_api_url_es,
        },
        settings.dapnet_callsign,
        settings.dapnet_password,
        default_server=settings.dapnet_default_server,
    )

    async def post_init(application: Application) -> None:
        await init_db(engine)
        await setup_commands(application)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["engine"] = engine
    application.bot_data["session_factory"] = session_factory
    application.bot_data["secret_box"] = secret_box
    application.bot_data["dapnet"] = dapnet

    register_handlers(application)
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError("JobQueue is not available; install python-telegram-bot[job-queue]")
    job_queue.run_repeating(
        sync_all_users,
        interval=timedelta(seconds=settings.sync_interval_seconds),
        first=10,
        name="caldav-sync",
    )
    job_queue.run_repeating(
        dispatch_due_reminders,
        interval=timedelta(seconds=settings.dispatch_interval_seconds),
        first=20,
        name="dapnet-dispatch",
    )
    return application


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = build_application(settings)
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
