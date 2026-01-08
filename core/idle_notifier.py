import asyncio
import time
import logging
from typing import Dict, Tuple

from core.chat_store_pg import init_pg, upsert_chat, load_chats

logger = logging.getLogger(__name__)

# key: ("vk", peer_id) или ("tg", chat_id), value: timestamp последней активности
_last_activity: Dict[Tuple[str, int], float] = {}


def touch(platform: str, chat_id: int) -> None:
    """Запоминаем чат (нужно для рассылок и чтобы бот 'помнил' чаты после деплоя)."""
    _last_activity[(platform, int(chat_id))] = time.time()

    # Сохраняем чат в Postgres, не блокируя обработку сообщений
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(asyncio.to_thread(upsert_chat, platform, int(chat_id)))
    except RuntimeError:
        # на всякий случай: если вызвали без event loop
        pass


def get_known_chats(platform: str | None = None):
    """Все известные чаты: лички + группы. Возвращает список [("tg", id), ("vk", id)]."""
    result = []
    for (plat, chat_id), _ts in _last_activity.items():
        if platform and plat != platform:
            continue
        result.append((plat, chat_id))
    return result


def get_group_chats(platform: str | None = None):
    """Только группы/беседы: TG chat_id < 0, VK peer_id >= 2_000_000_000."""
    result = []
    for (plat, chat_id), _ts in _last_activity.items():
        if platform and plat != platform:
            continue

        if plat == "tg":
            if chat_id < 0:
                result.append((plat, chat_id))
        elif plat == "vk":
            if chat_id >= 2_000_000_000:
                result.append((plat, chat_id))
    return result


async def init_known_chats():
    """Загрузка известных чатов из Postgres в память при старте приложения."""
    await asyncio.to_thread(init_pg)
    data = await asyncio.to_thread(load_chats)
    _last_activity.update(data)
