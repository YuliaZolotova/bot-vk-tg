from __future__ import annotations

import requests
from typing import Optional

from core.engine import OutAction, OutText, OutSticker, OutPhoto
from config import TG_TOKEN


def _tg(method: str, **kwargs):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/{method}"
    r = requests.post(url, timeout=20, **kwargs)
    return r.json()


def send_actions_tg(chat_id: int, actions: list[OutAction]):
    for a in actions:
        if isinstance(a, OutText):
            _tg("sendMessage", json={"chat_id": chat_id, "text": a.text})
        elif isinstance(a, OutSticker):
            _tg("sendSticker", json={"chat_id": chat_id, "sticker": a.file_id})
        elif isinstance(a, OutPhoto):
            with open(a.path, "rb") as f:
                _tg(
                    "sendPhoto",
                    data={"chat_id": str(chat_id), "caption": a.caption or ""},
                    files={"photo": f},
                )
