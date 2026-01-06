import time
import random
import requests
from settings import TG_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

def _typing_delay():
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))

def send_actions_tg(chat_id: int, actions):
    for action in actions:
        # 1) показать "печатает..."
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=10,
        )

        # 2) подождать 3-6 секунд
        _typing_delay()

        # 3) отправить сообщение
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": action.text},
            timeout=10,
        )
