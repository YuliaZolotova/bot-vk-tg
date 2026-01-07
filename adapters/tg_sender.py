from core.actions import OutText, OutPhoto
import requests

def send_actions_tg(chat_id: int, actions):
    if not actions:
        return

    # typing один раз
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction",
        json={"chat_id": chat_id, "action": "typing"},
        timeout=10,
    )
    _typing_delay()

    for action in actions:
        if isinstance(action, OutPhoto):
            with open(action.path, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id, "caption": action.caption or ""},
                    files={"photo": f},
                    timeout=30,
                )
        else:  # OutText
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": action.text},
                timeout=10,
            )
