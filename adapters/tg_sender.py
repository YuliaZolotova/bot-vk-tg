import time
import random
import requests

from settings import TG_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

def _typing_delay():
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))

def send_actions_tg(chat_id: int, actions):
    """Show typing once, wait a bit, then send all messages as a batch."""
    if not actions:
        return

    # 1) показать "печатает..." (один раз)
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction",
        json={"chat_id": chat_id, "action": "typing"},
        timeout=10,
    )

    # 2) подождать 3-6 секунд
    _typing_delay()

    # 3) отправить все сообщения подряд
    for action in actions:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": getattr(action, "text", "")},
            timeout=10,
        )

