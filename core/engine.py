from typing import List
from core.actions import OutText
from modules.simple_replies.handler import get_simple_reply

async def build_reply_actions(text: str, user_id: int, chat_id: int) -> List[OutText]:
    reply = get_simple_reply(text)
    if reply:
        return [reply]
    return []
