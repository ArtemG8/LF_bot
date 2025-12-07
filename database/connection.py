import asyncpg
from config import Config

async def create_db_pool():
    """Создание пула подключений к бд."""
    try:
        pool = await asyncpg.create_pool(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            min_size=5,
            max_size=10
        )
        print("Подключение к базе данных успешно установлено.")
        return pool
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}")
        return None


