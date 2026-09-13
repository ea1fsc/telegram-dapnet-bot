from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from telegram import Update
from telegram.ext import ContextTypes

from telegram_dapnet_bot.db import repo
from telegram_dapnet_bot.db.models import User, UserStatus
from telegram_dapnet_bot.db.session import session_scope


UNKNOWN_COMMAND_TEXT = (
    "I do not know that command. Use /help for the command menu."
)


def session_factory_of(
    context: ContextTypes.DEFAULT_TYPE,
) -> async_sessionmaker[AsyncSession]:
    return context.application.bot_data["session_factory"]


async def load_user(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> User | None:
    async with session_scope(session_factory_of(context)) as session:
        return await repo.get_user_by_telegram_id(session, telegram_id)


def is_admin(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> bool:
    return telegram_id in context.application.bot_data["settings"].admin_ids


def require_approved(
    handler: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any
    ) -> Any:
        user = update.effective_user
        message = update.effective_message
        if user is None or message is None:
            return None
        db_user = await load_user(context, user.id)
        if db_user is None:
            await message.reply_text(
                "You are not registered yet. Use /register to get started."
            )
            return None
        if db_user.status == UserStatus.PENDING:
            await message.reply_text(
                "Your registration is waiting for an administrator to approve it."
            )
            return None
        if db_user.status != UserStatus.APPROVED:
            await message.reply_text(
                "Your request was rejected. If that was a mistake, run /register again."
            )
            return None
        return await handler(update, context, db_user, *args, **kwargs)

    return wrapper


def require_admin(
    handler: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any
    ) -> Any:
        user = update.effective_user
        message = update.effective_message
        if user is None or not is_admin(context, user.id):
            if message is not None:
                await message.reply_text(UNKNOWN_COMMAND_TEXT)
            return None
        return await handler(update, context, *args, **kwargs)

    return wrapper
