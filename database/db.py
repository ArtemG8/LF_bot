import asyncpg
from typing import List, Dict, Optional, Any


class Database:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по тг ID"""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
            return dict(user) if user else None

    async def register_user(self, telegram_id: int, username: str) -> Optional[Dict[str, Any]]:
        """Регистрирует нового пользователя или возвращает существующего"""
        async with self.pool.acquire() as conn:
            try:
                user = await conn.fetchrow(
                    "INSERT INTO users (telegram_id, username) VALUES ($1, $2) "
                    "ON CONFLICT (telegram_id) DO UPDATE SET username = $2 RETURNING *",
                    telegram_id, username
                )
                return dict(user)
            except Exception as e:
                print(f"Ошибка при регистрации/обновлении пользователя: {e}")
                return None

    async def get_next_match(self) -> Optional[Dict[str, Any]]:
        """Получает ближайший будущий матч"""
        async with self.pool.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT * FROM matches WHERE match_datetime > NOW() AND status = 'upcoming' ORDER BY match_datetime "
                "ASC LIMIT 1 "
            )
            return dict(match) if match else None

    async def get_matches_for_month(self) -> List[Dict[str, Any]]:
        """Получает матчи на ближайший месяц"""
        async with self.pool.acquire() as conn:
            matches = await conn.fetch(
                "SELECT * FROM matches WHERE match_datetime BETWEEN NOW() AND NOW() + INTERVAL '1 month' ORDER BY "
                "match_datetime ASC "
            )
            return [dict(m) for m in matches]

    async def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Получает игрока по ID"""
        async with self.pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE id = $1", player_id)
            return dict(player) if player else None

    async def get_players_by_position(self, position: str) -> List[Dict[str, Any]]:
        """Получает список игроков по позиции"""
        async with self.pool.acquire() as conn:
            players = await conn.fetch("SELECT * FROM players WHERE position = $1 ORDER BY name ASC", position)
            return [dict(p) for p in players]

    async def get_user_team(self, user_id: int, match_id: int) -> Optional[Dict[str, Any]]:
        """Получает состав пользователя на конкретный матч"""
        async with self.pool.acquire() as conn:
            team = await conn.fetchrow(
                "SELECT * FROM user_teams WHERE user_id = $1 AND match_id = $2",
                user_id, match_id
            )
            return dict(team) if team else None

    async def save_user_team(self, user_id: int, match_id: int, player_ids: List[int]) -> None:
        """Сохраняет или обновляет состав пользователя на матч"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_teams (user_id, match_id, player_ids) VALUES ($1, $2, $3) "
                "ON CONFLICT (user_id, match_id) DO UPDATE SET player_ids = $3, updated_at = NOW()",
                user_id, match_id, player_ids
            )

    async def delete_user_team(self, user_id: int, match_id: int) -> None:
        """Удаляет состав пользователя на матч"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM user_teams WHERE user_id = $1 AND match_id = $2",
                user_id, match_id
            )

    async def get_last_user_team(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает последний состав пользователя"""
        async with self.pool.acquire() as conn:
            team = await conn.fetchrow(
                "SELECT * FROM user_teams WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1",
                user_id
            )
            return dict(team) if team else None

    async def get_player_names_from_ids(self, player_ids: List[int]) -> List[str]:
        """Получает имена игроков по списку ID"""
        if not player_ids:
            return []
        async with self.pool.acquire() as conn:
            players = await conn.fetch(
                "SELECT name FROM players WHERE id = ANY($1::int[]) ORDER BY position, name", player_ids
            )
            return [p['name'] for p in players]

    async def get_user_team_with_names(self, user_id: int, match_id: int) -> Optional[Dict[str, Any]]:
        """Получает состав пользователя на матч с именами игроков"""
        team_data = await self.get_user_team(user_id, match_id)
        if team_data:
            player_names = await self.get_player_names_from_ids(team_data['player_ids'])
            team_data['player_names'] = player_names
        return team_data

    async def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Получает данные для таблицы лидеров"""
        async with self.pool.acquire() as conn:
            leaderboard = await conn.fetch(
                "SELECT username, total_score FROM users ORDER BY total_score DESC LIMIT 10"
            )
            return [dict(row) for row in leaderboard]

    # --- Admin-specific functions ---
    async def get_finished_unscored_matches(self) -> List[Dict[str, Any]]:
        """Получает завершенные матчи, для которых еще не введены очки"""
        async with self.pool.acquire() as conn:
            matches = await conn.fetch(
                "SELECT * FROM matches WHERE status = 'finished' AND is_scored = FALSE ORDER BY match_datetime DESC"
            )
            return [dict(m) for m in matches]

    async def get_all_players(self) -> List[Dict[str, Any]]:
        """Получает всех игроков"""
        async with self.pool.acquire() as conn:
            players = await conn.fetch("SELECT * FROM players ORDER BY position, name")
            return [dict(p) for p in players]

    async def save_player_points(self, match_id: int, player_id: int, points: float) -> None:
        """Сохраняет очки игрока за матч"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO match_player_points (match_id, player_id, points) VALUES ($1, $2, $3) "
                "ON CONFLICT (match_id, player_id) DO UPDATE SET points = $3",
                match_id, player_id, points
            )

    async def update_user_scores_for_match(self, match_id: int) -> None:
        """Пересчитывает и обновляет очки пользователей за конкретный матч и их общий рейтинг"""
        async with self.pool.acquire() as conn:
            # 1. Получаем очки игроков за данный матч
            player_points = await conn.fetch(
                "SELECT player_id, points FROM match_player_points WHERE match_id = $1", match_id
            )
            player_points_map = {p['player_id']: p['points'] for p in player_points}

            # 2. Получаем все пользовательские команды на этот матч
            user_teams = await conn.fetch(
                "SELECT user_id, player_ids FROM user_teams WHERE match_id = $1", match_id
            )

            # 3. Пересчитываем очки для каждого пользователя
            user_scores = {}
            for team in user_teams:
                user_id = team['user_id']
                team_score = 0.0
                for player_id in team['player_ids']:
                    team_score += player_points_map.get(player_id, 0.0)
                user_scores[user_id] = team_score

            async with conn.transaction():
                for user_id, score in user_scores.items():
                    # Обновляем или вставляем счет пользователя за этот матч
                    await conn.execute(
                        "INSERT INTO user_match_scores (user_id, match_id, score) VALUES ($1, $2, $3) "
                        "ON CONFLICT (user_id, match_id) DO UPDATE SET score = $3",
                        user_id, match_id, score
                    )

                    total_score = await conn.fetchval(
                        "SELECT SUM(score) FROM user_match_scores WHERE user_id = $1", user_id
                    )
                    await conn.execute(
                        "UPDATE users SET total_score = $1 WHERE id = $2",
                        total_score if total_score is not None else 0.0, user_id
                    )

                # 5. Отмечаем матч как оцененный
                await conn.execute(
                    "UPDATE matches SET is_scored = TRUE WHERE id = $1", match_id
                )
            print(f"Очки пользователей и общий рейтинг обновлены для матча {match_id}")

    async def set_match_status(self, match_id: int, status: str) -> None:
        """Устанавливает статус матча"""
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE matches SET status = $1 WHERE id = $2", status, match_id)

    async def get_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Получает детали матча по ID"""
        async with self.pool.acquire() as conn:
            match = await conn.fetchrow("SELECT * FROM matches WHERE id = $1", match_id)
            return dict(match) if match else None
