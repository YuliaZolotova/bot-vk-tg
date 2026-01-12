import time
import random
import requests

from core.actions import OutText, OutPhoto
from settings import VK_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

VK_API_VERSION = "5.199"


def _typing_delay():
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))


def _vk_call(method: str, params: dict, timeout: int = 20) -> dict:
    params = dict(params)
    params["access_token"] = VK_TOKEN
    params["v"] = VK_API_VERSION
    r = requests.post(f"https://api.vk.com/method/{method}", data=params, timeout=timeout)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"VK API error in {method}: {data['error']}")
    return data["response"]


def _vk_upload_message_photo(peer_id: int, file_path: str) -> str:
    server = _vk_call("photos.getMessagesUploadServer", {"peer_id": peer_id})
    upload_url = server["upload_url"]

    with open(file_path, "rb") as f:
        up_resp = requests.post(upload_url, files={"photo": f}, timeout=30)
        up = up_resp.json()

    # на всякий случай проверим, что нужные поля есть
    if not all(k in up for k in ("photo", "server", "hash")):
        raise RuntimeError(f"VK upload response missing fields: {up}")

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
    """
    ВАЖНО:
    - НИКОГДА не кидаем исключение наружу, чтобы VK не ретраил webhook.
    - random_id делаем уникальным, чтобы VK не дублировал сообщения.
    - Если фото не отправилось — отправим хотя бы текст (описание).
    """
    if not actions:
        return

    # 1) "печатает..."
    try:
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
    except Exception:
        pass

    # 2) задержка
    try:
        _typing_delay()
    except Exception:
        pass

    # 3) отправка
    for action in actions:
        rid = random.randint(1, 2_000_000_000)

        try:
            if isinstance(action, OutPhoto):
                attachment = _vk_upload_message_photo(peer_id, action.path)
                _vk_call(
                    "messages.send",
                    {
                        "peer_id": peer_id,
                        "random_id": rid,
                        "message": action.caption or "",
                        "attachment": attachment,
                    },
                )
            else:
                _vk_call(
                    "messages.send",
                    {
                        "peer_id": peer_id,
                        "random_id": rid,
                        "message": action.text,
                    },
                )

        except Exception as e:
            # НЕ ПАДАЕМ. Пытаемся отправить fallback-текст, чтобы пользователь получил хоть что-то.
            try:
                _vk_call(
                    "messages.send",
                    {
                        "peer_id": peer_id,
                        "random_id": random.randint(1, 2_000_000_000),
                        "message": "⚠️ Не получилось отправить картинку (это особенность Вк), но вот текст карты дня:",
                    },
                )
            except Exception:
                pass
            # дальше продолжаем, чтобы не терять следующие OutText
            continue
