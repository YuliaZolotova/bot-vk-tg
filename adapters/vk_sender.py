import time
import random
import requests

from core.actions import OutText, OutPhoto
from settings import VK_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

VK_API_VERSION = "5.199"

def _typing_delay():
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))

def _vk_call(method: str, params: dict, timeout: int = 20) -> dict:
    """Вызов VK API, возвращает json['response'] или кидает ошибку."""
    params = dict(params)
    params["access_token"] = VK_TOKEN
    params["v"] = VK_API_VERSION
    r = requests.post(f"https://api.vk.com/method/{method}", data=params, timeout=timeout)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"VK API error in {method}: {data['error']}")
    return data["response"]

def _vk_upload_message_photo(peer_id: int, file_path: str) -> str:
    """
    Загружает локальный файл в ВК как фото для сообщений.
    Возвращает строку attachment вида photo{owner_id}_{id}_{access_key?}
    """
    server = _vk_call("photos.getMessagesUploadServer", {"peer_id": peer_id})
    upload_url = server["upload_url"]

    with open(file_path, "rb") as f:
        up = requests.post(upload_url, files={"photo": f}, timeout=30).json()

    saved = _vk_call(
        "photos.saveMessagesPhoto",
        {"photo": up["photo"], "server": up["server"], "hash": up["hash"]},
    )[0]

    owner_id = saved["owner_id"]
    photo_id = saved["id"]
    access_key = saved.get("access_key")

    attachment = f"photo{owner_id}_{photo_id}"
    if access_key:
        attachment += f"_{access_key}"
    return attachment


def send_actions_vk(peer_id: int, actions):
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

    # 2) подождать 3–6 секунд
    _typing_delay()

    # 3) отправить все действия подряд
    for action in actions:
        if isinstance(action, OutPhoto):
            attachment = _vk_upload_message_photo(peer_id, action.path)
            _vk_call(
                "messages.send",
                {
                    "peer_id": peer_id,
                    "random_id": 0,
                    "message": action.caption or "",
                    "attachment": attachment,
                },
            )
        else:  # OutText
            _vk_call(
                "messages.send",
                {
                    "peer_id": peer_id,
                    "random_id": 0,
                    "message": action.text,
                },
            )

