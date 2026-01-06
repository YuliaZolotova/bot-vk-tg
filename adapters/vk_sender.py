from __future__ import annotations
import os
import requests
from core.types import Action, OutText, OutPhoto
from config import VK_TOKEN

_VK_API = "https://api.vk.com/method/{method}"
_VK_VER = "5.199"

def _vk(method: str, params: dict):
    if not VK_TOKEN:
        raise RuntimeError("VK_TOKEN is not set")
    p = dict(params)
    p.update({"access_token": VK_TOKEN, "v": _VK_VER})
    r = requests.post(_VK_API.format(method=method), data=p, timeout=30)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"VK API error: {data['error']}")
    return data["response"]

def _upload_message_photo(peer_id: int, path: str) -> str | None:
    if not os.path.exists(path):
        return None
    server = _vk("photos.getMessagesUploadServer", {"peer_id": peer_id})
    upload_url = server["upload_url"]

    with open(path, "rb") as f:
        up = requests.post(upload_url, files={"photo": f}, timeout=60).json()

    saved = _vk("photos.saveMessagesPhoto", {"photo": up["photo"], "server": up["server"], "hash": up["hash"]})
    photo = saved[0]
    owner_id = photo["owner_id"]
    photo_id = photo["id"]
    access_key = photo.get("access_key")
    if access_key:
        return f"photo{owner_id}_{photo_id}_{access_key}"
    return f"photo{owner_id}_{photo_id}"

def send_actions_vk(peer_id: int, actions: list[Action]) -> None:
    for a in actions:
        if isinstance(a, OutText):
            _vk("messages.send", {"peer_id": peer_id, "random_id": 0, "message": a.text})
        elif isinstance(a, OutPhoto):
            attach = _upload_message_photo(peer_id, a.path)
            params = {"peer_id": peer_id, "random_id": 0, "message": a.caption or ""}
            if attach:
                params["attachment"] = attach
            _vk("messages.send", params)
