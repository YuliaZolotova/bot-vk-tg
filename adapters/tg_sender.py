from __future__ import annotations
import os
import requests
from core.types import Action, OutText, OutPhoto
from config import TG_TOKEN

_API = "https://api.telegram.org/bot{token}/{method}"

def _url(method: str) -> str:
    return _API.format(token=TG_TOKEN, method=method)

def send_actions_tg(chat_id: int, actions: list[Action]) -> None:
    if not TG_TOKEN:
        raise RuntimeError("TG_TOKEN is not set")

    for a in actions:
        if isinstance(a, OutText):
            requests.post(_url("sendMessage"), json={"chat_id": chat_id, "text": a.text}, timeout=20)
        elif isinstance(a, OutPhoto):
            if not a.path or not os.path.exists(a.path):
                if a.caption:
                    requests.post(_url("sendMessage"), json={"chat_id": chat_id, "text": a.caption}, timeout=20)
                continue
            with open(a.path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": str(chat_id), "caption": a.caption or ""}
                requests.post(_url("sendPhoto"), data=data, files=files, timeout=60)
