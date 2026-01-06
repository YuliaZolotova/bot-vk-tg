import requests
from settings import TG_TOKEN

def send_actions_tg(chat_id, actions):
    for action in actions:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": action.text}
        )
