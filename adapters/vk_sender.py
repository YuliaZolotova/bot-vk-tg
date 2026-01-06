import requests
from settings import VK_TOKEN

def send_actions_vk(peer_id, actions):
    for action in actions:
        requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "peer_id": peer_id,
                "random_id": 0,
                "message": action.text,
                "access_token": VK_TOKEN,
                "v": "5.199",
            }
        )