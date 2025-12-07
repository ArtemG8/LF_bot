from config import Config


async def create_tables(conn):
    """Создает необходимые таблицы в базе данных."""
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
            status VARCHAR(50) DEFAULT 'upcoming', -- 'upcoming', 'finished'
            is_scored BOOLEAN DEFAULT FALSE, -- Для отслеживания, были ли введены очки
            UNIQUE(opponent, match_datetime) -- <-- ДОБАВЛЕНО: Уникальный индекс для матчей
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            position VARCHAR(50) NOT NULL -- 'goalkeeper', 'defender', 'midfielder', 'forward'
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_teams (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            player_ids INTEGER[] NOT NULL, -- Массив ID игроков
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, match_id) -- Пользователь может иметь только один состав на матч
        );
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS match_player_points (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            points REAL NOT NULL,
            UNIQUE(match_id, player_id) -- Очки для игрока по матчу только одни
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

    print("Таблицы созданы или уже существуют")


async def insert_initial_data(conn):
    """Вставляет начальные данные если их нет"""
    # Вставка игроков
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
    print("Начальные данные вставлены или уже существуют.")

