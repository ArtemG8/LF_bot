from aiogram import Bot
from aiogram.types import BotCommand


async def set_main_menu(bot: Bot):
    """Устанавливает главное меню для бота."""
    main_menu_commands = [
        BotCommand(command='/start', description="Старт бота"),
        BotCommand(command='/myteam', description='Мой состав'),
        BotCommand(command='/pickteam', description='Выбор состава'),
        BotCommand(command='/resetteam', description='Сбросить состав'),
        BotCommand(command='/leaderboard', description='Таблица рейтинга'),
    ]
    await bot.set_my_commands(main_menu_commands)
