from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from telegram_dapnet_bot.db.models import Base
from telegram_dapnet_bot.db.repo import backfill_user_rics_from_csv


def create_engine(database_url: str) -> AsyncEngine:
    if database_url.startswith("sqlite"):
        db_path = database_url.split("///", 1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(database_url, echo=False)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _add_missing_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "dapnet_rics" not in columns:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN dapnet_rics VARCHAR(255) DEFAULT ''")
        )
    if "dapnet_server" not in columns:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN dapnet_server VARCHAR(8) DEFAULT 'de'")
        )


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
    factory = create_session_factory(engine)
    async with factory() as session:
        await backfill_user_rics_from_csv(session)
        await session.commit()


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
