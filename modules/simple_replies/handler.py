import random
from core.actions import OutText
from .rules import RULES


async def get_simple_reply(text: str, user_id: int, chat_id: int, source: str = "unknown"):
    low = (text or "").lower()
    for rule in RULES:
        if any(t in low for t in rule["triggers"]):
            return [OutText(random.choice(rule["responses"]))]
    return None
