from typing import List
from core.actions import OutText
from modules.simple_replies.handler import get_simple_reply
from modules.tarot_day.handler import get_tarot_day_reply


async def build_reply_actions(text: str, user_id: int, chat_id: int, source: str = "unknown"):
    # 1️⃣ Карта дня
    actions = get_tarot_day_reply(text, user_id, source=source)
    if actions:
        return actions

    # 2️⃣ Простые ответы
    actions = await get_simple_reply(text, user_id, chat_id)
    return actions

