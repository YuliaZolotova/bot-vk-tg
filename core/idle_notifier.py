import asyncio
import time
import random
import logging
from typing import Dict, Tuple

from settings import IDLE_TIMEOUT_SECONDS, IDLE_CHECK_EVERY_SECONDS, IDLE_MESSAGES
from core.actions import OutText
from adapters.vk_sender import send_actions_vk
from adapters.tg_sender import send_actions_tg
import asyncio
from core.chat_store_pg import init_pg, upsert_chat, load_chats


logger = logging.getLogger(__name__)

# ключ: ("vk", peer_id) или ("tg", chat_id)
_last_activity: Dict[Tuple[str, int], float] = {}


def touch(platform: str, chat_id: int) -> None:
    """Вызывай при каждом входящем сообщении, чтобы помнить 'последнюю активность' чата."""
    _last_activity[(platform, int(chat_id))] = time.time()
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(asyncio.to_thread(upsert_chat, platform, int(chat_id)))
    except RuntimeError:
        pass



async def _send_idle_message(platform: str, chat_id: int) -> None:
    text = random.choice(IDLE_MESSAGES)
    actions = [OutText(text=text)]

    if platform == "vk":
        send_actions_vk(chat_id, actions)
    elif platform == "tg":
        send_actions_tg(chat_id, actions)


async def idle_loop() -> None:
    """Фоновый цикл: если чат молчит N секунд — бот пишет сообщение."""
    await asyncio.sleep(5)  # небольшая пауза после старта приложения
    logger.info("Idle notifier started")

    while True:
        try:
            now = time.time()
            items = list(_last_activity.items())  # копия, чтобы не падать при изменении dict

            for (platform, chat_id), last_ts in items:
                if now - last_ts >= IDLE_TIMEOUT_SECONDS:
                    await _send_idle_message(platform, chat_id)
                    # обновляем время, чтобы не спамить на каждой проверке
                    _last_activity[(platform, chat_id)] = time.time()

        except Exception:
            logger.exception("Idle notifier error")

        await asyncio.sleep(IDLE_CHECK_EVERY_SECONDS)

def get_known_chats(platform: str | None = None):
    """
    Все чаты, которые бот видел (и лички, и группы).
    Возвращает [("tg", chat_id), ("vk", peer_id), ...]
    """
    items = list(_last_activity.keys())
    if platform:
        items = [x for x in items if x[0] == platform]
    return items


def get_group_chats(platform: str | None = None):
    """
    Только группы/беседы (без личек).
    """
    result = []
    for plat, chat_id in get_known_chats(platform):
        if plat == "tg":
            # в TG группы/супергруппы обычно отрицательные id
            if chat_id < 0:
                result.append((plat, chat_id))
        elif plat == "vk":
            # в VK беседы >= 2_000_000_000
            if chat_id >= 2_000_000_000:
                result.append((plat, chat_id))
    return result

async def init_known_chats():
    # создать таблицу + загрузить чаты
    await asyncio.to_thread(init_pg)
    data = await asyncio.to_thread(load_chats)
    _last_activity.update(data)


