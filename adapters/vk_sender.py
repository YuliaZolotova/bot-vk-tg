from __future__ import annotations

import os
import time
import requests
from typing import Optional

from core.engine import OutAction, OutText, OutSticker, OutPhoto
from config import VK_TOKEN


VK_API_VERSION = "5.131"


def _vk(method: str, data: dict):
    payload = {"access_token": VK_TOKEN, "v": VK_API_VERSION, **data}
    r = requests.post(f"https://api.vk.com/method/{method}", data=payload, timeout=15)
    return r.json()


def _upload_photo(peer_id: int, photo_path: str) -> Optional[str]:
    """Upload a local photo and return attachment string like 'photo{owner_id}_{id}'."""
    server_resp = _vk("photos.getMessagesUploadServer", {"peer_id": peer_id})
    upload_url = server_resp.get("response", {}).get("upload_url")
    if not upload_url:
        return None

    with open(photo_path, "rb") as f:
        up = requests.post(upload_url, files={"photo": f}, timeout=30).json()

    save_resp = _vk(
        "photos.saveMessagesPhoto",
        {
            "photo": up.get("photo"),
            "server": up.get("server"),
            "hash": up.get("hash"),
        },
    )
    items = save_resp.get("response") or []
    if not items:
        return None

    ph = items[0]
    return f"photo{ph['owner_id']}_{ph['id']}"


def send_actions_vk(peer_id: int, actions: list[OutAction]):
    for a in actions:
        if isinstance(a, OutText):
            _vk("messages.send", {"peer_id": peer_id, "message": a.text, "random_id": int(time.time() * 1000)})
        elif isinstance(a, OutPhoto):
            attachment = _upload_photo(peer_id, a.path)
            if attachment:
                _vk(
                    "messages.send",
                    {
                        "peer_id": peer_id,
                        "message": a.caption or "",
                        "attachment": attachment,
                        "random_id": int(time.time() * 1000),
                    },
                )
            else:
                # fallback to caption text only
                if a.caption:
                    _vk("messages.send", {"peer_id": peer_id, "message": a.caption, "random_id": int(time.time() * 1000)})
        elif isinstance(a, OutSticker):
            # VK can't send Telegram sticker ids -> send a small note instead
            _vk("messages.send", {"peer_id": peer_id, "message": "🙂", "random_id": int(time.time() * 1000)})
