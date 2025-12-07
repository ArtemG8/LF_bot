import asyncpg
import datetime
from config import Config


async def create_tables(conn):
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            total_score REAL DEFAULT 0.0,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            opponent VARCHAR(255) NOT NULL,
            match_datetime TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            status VARCHAR(50) DEFAULT 'upcoming',
            is_scored BOOLEAN DEFAULT FALSE,
            UNIQUE(opponent, match_datetime)
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            position VARCHAR(50) NOT NULL
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_teams (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            player_ids INTEGER[] NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, match_id)
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS match_player_points (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            points REAL NOT NULL,
            UNIQUE(match_id, player_id)
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_match_scores (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            score REAL DEFAULT 0.0,
            UNIQUE(user_id, match_id)
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            id SERIAL PRIMARY KEY,
            setting_name VARCHAR(255) UNIQUE NOT NULL,
            setting_value TEXT
        );
    ''')

    print("Таблицы созданы или уже существуют.")


async def insert_initial_data(conn):
    for position, player_names in Config.PLAYERS.items():
        for player_name in player_names:
            await conn.execute('''
                INSERT INTO players (name, position) VALUES ($1, $2)
                ON CONFLICT (name) DO NOTHING;
            ''', player_name, position)

    await conn.execute('''
        INSERT INTO matches (opponent, match_datetime, status, is_scored) VALUES
        ('Manchester United', '2025-12-08 20:00:00', 'upcoming', FALSE),
        ('Everton', '2025-12-15 15:00:00', 'upcoming', FALSE),
        ('Chelsea', '2025-12-22 17:30:00', 'upcoming', FALSE),
        ('Arsenal', '2025-11-20 20:00:00', 'finished', TRUE)
        ON CONFLICT (opponent, match_datetime) DO NOTHING;
    ''')

    default_password = Config.DEFAULT_ADMIN_PASSWORD
    await conn.execute('''
        INSERT INTO admin_settings (setting_name, setting_value) VALUES ('admin_password', $1)
        ON CONFLICT (setting_name) DO NOTHING;
    ''', default_password)

    print("Начальные данные вставлены или уже существуют.")

