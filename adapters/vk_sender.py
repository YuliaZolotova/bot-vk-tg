import time
import random
import requests
from settings import VK_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

VK_API_VERSION = "5.199"

def _typing_delay():
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))

def send_actions_vk(peer_id: int, actions):
    for action in actions:
        # 1) показать "печатает..."
        requests.post(
            "https://api.vk.com/method/messages.setActivity",
            data={
                "access_token": VK_TOKEN,
                "v": VK_API_VERSION,
                "peer_id": peer_id,
                "type": "typing",
            },
            timeout=10,
        )

        # 2) подождать 3-6 секунд
        _typing_delay()

        # 3) отправить сообщение
        requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "access_token": VK_TOKEN,
                "v": VK_API_VERSION,
                "peer_id": peer_id,
                "random_id": 0,
                "message": action.text,
            },
            timeout=10,
        )
