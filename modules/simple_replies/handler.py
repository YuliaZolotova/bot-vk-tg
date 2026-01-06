import random
from core.actions import OutText
from .rules import RULES

def get_simple_reply(text: str):
    low = (text or "").lower()
    for rule in RULES:
        if any(t in low for t in rule["triggers"]):
            return OutText(text=random.choice(rule["responses"]))
    return None
