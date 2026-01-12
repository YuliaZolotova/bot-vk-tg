import os
from typing import Dict, Tuple
from datetime import date

import psycopg2


def _dsn() -> str:
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return dsn


def _get_conn():
    return psycopg2.connect(_dsn())


def init_who_today_tables():
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_users (
                    platform TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    display_name TEXT,
                    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (platform, chat_id, user_id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS who_today_assignments (
                    platform TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    day DATE NOT NULL,
                    user_id BIGINT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (platform, chat_id, day, user_id)
                );
            """)
        conn.commit()
    finally:
        conn.close()


def touch_chat_user(platform: str, chat_id: int, user_id: int, display_name: str | None = None):
    """
    Запоминаем, что пользователь писал в этом чате.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_users (platform, chat_id, user_id, display_name, last_seen)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (platform, chat_id, user_id)
                DO UPDATE SET
                    display_name = COALESCE(EXCLUDED.display_name, chat_users.display_name),
                    last_seen = NOW();
            """, (platform, int(chat_id), int(user_id), display_name))
        conn.commit()
    finally:
        conn.close()


def get_available_users_for_today(platform: str, chat_id: int, day: date, limit: int = 200) -> list[tuple[int, str | None]]:
    """
    Возвращает пользователей этого чата, которые ещё НЕ получали титул сегодня.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.user_id, u.display_name
                FROM chat_users u
                WHERE u.platform = %s AND u.chat_id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM who_today_assignments a
                      WHERE a.platform = u.platform
                        AND a.chat_id = u.chat_id
                        AND a.day = %s
                        AND a.user_id = u.user_id
                  )
                ORDER BY u.last_seen DESC
                LIMIT %s;
            """, (platform, int(chat_id), day, int(limit)))
            rows = cur.fetchall()
            return [(int(r[0]), r[1]) for r in rows]
    finally:
        conn.close()


def assign_title_today(platform: str, chat_id: int, day: date, user_id: int, title: str):
    """
    Фиксируем: этому пользователю в этом чате сегодня уже дали титул.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO who_today_assignments (platform, chat_id, day, user_id, title)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (platform, int(chat_id), day, int(user_id), title))
        conn.commit()
    finally:
        conn.close()



#----------------1-----------------
def _dsn() -> str:
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return dsn


def init_pg() -> None:
    """Создаём таблицу, если её ещё нет."""
    with psycopg2.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS known_chats (
                    platform TEXT NOT NULL,
                    chat_id  BIGINT NOT NULL,
                    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (platform, chat_id)
                );
                """
            )
        conn.commit()


def upsert_chat(platform: str, chat_id: int) -> None:
    """Запоминаем чат (или обновляем last_seen)."""
    with psycopg2.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO known_chats(platform, chat_id, last_seen)
                VALUES (%s, %s, NOW())
                ON CONFLICT (platform, chat_id)
                DO UPDATE SET last_seen = NOW();
                """,
                (platform, int(chat_id)),
            )
        conn.commit()


def load_chats() -> Dict[Tuple[str, int], float]:
    """Загружаем список чатов из БД в формат, удобный для _last_activity."""
    out: Dict[Tuple[str, int], float] = {}
    with psycopg2.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT platform, chat_id FROM known_chats;")
            for platform, chat_id in cur.fetchall():
                out[(platform, int(chat_id))] = 0.0
    return out

# Статистика Ангельского времени
def init_angel_time_stats() -> None:
    """Таблица для статистики 'ангельского времени'."""
    with psycopg2.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS angel_time_stats (
                    id SERIAL PRIMARY KEY,
                    platform TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    time_value TEXT NOT NULL,
                    seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()


def log_angel_time(platform: str, chat_id: int, user_id: int, time_value: str) -> None:
    """Записать, что пользователь увидел время."""
    with psycopg2.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO angel_time_stats (platform, chat_id, user_id, time_value)
                VALUES (%s, %s, %s, %s);
                """,
                (platform, int(chat_id), int(user_id), time_value),
            )
        conn.commit()


def get_user_angel_stats(platform: str, chat_id: int, user_id: int, limit: int = 5) -> tuple[int, list[tuple[str, int]]]:
    """
    Возвращает:
      - total (сколько раз всего видел ангельское время в этом чате)
      - top: список (time_value, count) топ-N
    """
    with psycopg2.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM angel_time_stats
                WHERE platform=%s AND chat_id=%s AND user_id=%s;
                """,
                (platform, int(chat_id), int(user_id)),
            )
            total = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT time_value, COUNT(*) AS c
                FROM angel_time_stats
                WHERE platform=%s AND chat_id=%s AND user_id=%s
                GROUP BY time_value
                ORDER BY c DESC, time_value ASC
                LIMIT %s;
                """,
                (platform, int(chat_id), int(user_id), int(limit)),
            )
            top = [(str(t), int(c)) for (t, c) in cur.fetchall()]

    def get_who_today_title_stats(platform: str, chat_id: int, limit: int = 10) -> list[tuple[str, int]]:
        """
        Топ титулов в этом чате за всё время.
        Возвращает: [(title, count), ...]
        """
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                            SELECT title, COUNT(*) as c
                            FROM who_today_assignments
                            WHERE platform = %s
                              AND chat_id = %s
                            GROUP BY title
                            ORDER BY c DESC, title ASC
                                LIMIT %s;
                            """, (platform, int(chat_id), int(limit)))
                rows = cur.fetchall()
                return [(str(t), int(c)) for (t, c) in rows]
        finally:
            conn.close()

    def get_who_today_title_stats_today(platform: str, chat_id: int, day: date, limit: int = 10) -> list[
        tuple[str, int]]:
        """
        Топ титулов в этом чате за конкретную дату (обычно сегодня).
        """
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                            SELECT title, COUNT(*) as c
                            FROM who_today_assignments
                            WHERE platform = %s AND chat_id = %s AND day = %s
                            GROUP BY title
                            ORDER BY c DESC, title ASC
                                LIMIT %s;
                            """, (platform, int(chat_id), day, int(limit)))
                rows = cur.fetchall()
                return [(str(t), int(c)) for (t, c) in rows]
        finally:
            conn.close()

    return total, top


