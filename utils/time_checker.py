from __future__ import annotations
from datetime import datetime
import pytz
from config import TZ

_TIME_TRIGGERS = [
    "время",
    "который час",
    "сколько времени",
    "часов",
]

def is_time_request(text: str) -> bool:
    low = (text or "").lower()
    return any(t in low for t in _TIME_TRIGGERS)

def get_time_reply() -> str:
    tz = pytz.timezone(TZ)
    now = datetime.now(tz)
    return f"Сейчас {now.strftime('%H:%M')} ({TZ})."
