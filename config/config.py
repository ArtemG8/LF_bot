import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "adminpass")

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")

    POSITIONS = {
        "goalkeeper": "Вратари 🧤",
        "defender": "Защитники 🛡️",
        "midfielder": "Полузащитники ⚙️",
        "forward": "Нападающие 🎯"
    }

    MATCHES_PER_PAGE = 5