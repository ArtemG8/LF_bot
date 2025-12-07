from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import Database


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db_session: Database):
        self.db_session = db_session

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db_session
        return await handler(event, data)
