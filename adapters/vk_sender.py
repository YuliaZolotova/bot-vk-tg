import time
import random
import requests

from settings import VK_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

VK_API_VERSION = "5.199"

def _typing_delay():
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))

def send_actions_vk(peer_id: int, actions):
    """Show typing once, wait a bit, then send all messages as a batch."""
    if not actions:
        return

    # 1) показать "печатает..." (один раз)
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

    # 3) отправить все сообщения подряд
    for action in actions:
        requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "access_token": VK_TOKEN,
                "v": VK_API_VERSION,
                "peer_id": peer_id,
                "random_id": random.randint(1, 2_147_483_647),
                "message": getattr(action, "text", ""),
            },
            timeout=10,
        )

