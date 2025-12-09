from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import Database


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db_session: Database, bot):
        self.db_session = db_session
        self.bot = bot

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db_session
        data["bot"] = self.bot
        return await handler(event, data)
