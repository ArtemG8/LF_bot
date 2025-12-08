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


NEW_PLAYERS_DATA = [
    {"name": "Alisson", "position": "goalkeeper"},
    {"name": "Giorgi Mamardashvili", "position": "goalkeeper"},
    {"name": "Freddie Woodman", "position": "goalkeeper"},


    {"name": "Ibrahima Konaté", "position": "defender"},
    {"name": "Giovanni Leoni", "position": "defender"},
    {"name": "Virgil van Dijk", "position": "defender"},
    {"name": "Joe Gomez", "position": "defender"},
    {"name": "Rhys Williams", "position": "defender"},
    {"name": "Milos Kerkez", "position": "defender"},
    {"name": "Andrew Robertson", "position": "defender"},
    {"name": "Jeremie Frimpong", "position": "defender"},
    {"name": "Conor Bradley", "position": "defender"},
    {"name": "Andy Robertson", "position": "defender"},
    {"name": "Calvin Ramsay", "position": "defender"},

    {"name": "Ryan Gravenberch", "position": "midfielder"},
    {"name": "Stefan Bajcetic", "position": "midfielder"},
    {"name": "Wataru Endo", "position": "midfielder"},
    {"name": "Alexis Mac Allister", "position": "midfielder"},
    {"name": "Curtis Jones", "position": "midfielder"},
    {"name": "Trey Nyoni", "position": "midfielder"},
    {"name": "Florian Wirtz", "position": "midfielder"},
    {"name": "Dominik Szoboszlai", "position": "midfielder"},

    {"name": "Cody Gakpo", "position": "forward"},
    {"name": "Rio Ngumoha", "position": "forward"},
    {"name": "Mohamed Salah", "position": "forward"},
    {"name": "Federico Chiesa", "position": "forward"},
    {"name": "Alexander Isak", "position": "forward"},
    {"name": "Hugo Ekitiké", "position": "forward"},
]


async def insert_initial_data(conn):
    for player_data in NEW_PLAYERS_DATA:
        await conn.execute('''
            INSERT INTO players (name, position) VALUES ($1, $2)
            ON CONFLICT (name) DO NOTHING;
        ''', player_data["name"], player_data["position"])

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
