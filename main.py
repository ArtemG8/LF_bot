import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from config import Config
from database import create_db_pool, create_tables, insert_initial_data, Database
from keyboards.set_menu import set_main_menu
from middlewares import DatabaseMiddleware
from handlers import private_user

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    db_pool = await create_db_pool()
    if not db_pool:
        logging.error("Не удалось подключиться к базе данных. Завершение работы.")
        return

    async with db_pool.acquire() as conn:
        await create_tables(conn)
        await insert_initial_data(conn)

    db = Database(db_pool)

    # middleware для передачи db в хэндлеры
    dp.message.middleware(DatabaseMiddleware(db, bot))
    dp.callback_query.middleware(DatabaseMiddleware(db, bot))

    dp.include_router(private_user.router)
    await set_main_menu(bot)
    logging.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

    # close пул БД при завершении работы
    await db_pool.close()
    logging.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот выключен.")
