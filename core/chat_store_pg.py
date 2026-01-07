import os
from typing import Dict, Tuple

import psycopg2


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
