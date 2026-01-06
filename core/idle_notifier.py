import asyncio
import time
import random
import logging
from typing import Dict, Tuple

from settings import IDLE_TIMEOUT_SECONDS, IDLE_CHECK_EVERY_SECONDS, IDLE_MESSAGES
from core.actions import OutText
from adapters.vk_sender import send_actions_vk
from adapters.tg_sender import send_actions_tg

logger = logging.getLogger(__name__)

# ключ: ("vk", peer_id) или ("tg", chat_id)
_last_activity: Dict[Tuple[str, int], float] = {}


def touch(platform: str, chat_id: int) -> None:
    """Вызывай при каждом входящем сообщении, чтобы помнить 'последнюю активность' чата."""
    _last_activity[(platform, int(chat_id))] = time.time()


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
