from __future__ import annotations
from datetime import datetime, timedelta
import os
import pytz
import ephem
from config import TZ

def _load_lunar_descriptions(filename: str) -> dict[int, str]:
    descriptions: dict[int, str] = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                try:
                    descriptions[int(key)] = value.strip().replace("\\n", "\n")
                except Exception:
                    continue
    except FileNotFoundError:
        return {}
    return descriptions

_DESCR_PATH = os.path.join(os.path.dirname(__file__), "lunar_descriptions.txt")
LUNAR_DESCRIPTIONS = _load_lunar_descriptions(_DESCR_PATH)

def get_lunar_day_and_end_time():
    tz = pytz.timezone(TZ)
    now = datetime.now(tz)

    last_new_moon = ephem.previous_new_moon(now)
    last_new_moon_local = last_new_moon.datetime().replace(tzinfo=pytz.utc).astimezone(tz)

    delta_days = (now - last_new_moon_local).days
    lunar_day = (delta_days % 29) + 1

    end_of_lunar_day = last_new_moon_local + timedelta(days=delta_days + 1)
    return lunar_day, end_of_lunar_day

def get_lunar_text() -> str:
    lunar_day, end_of_lunar_day = get_lunar_day_and_end_time()
    description = LUNAR_DESCRIPTIONS.get(lunar_day, "Описание не найдено.")
    return (
        f"Сейчас продолжается {lunar_day} лунный день.\n\n"
        f"{description}\n\n"
        f"Окончание: {end_of_lunar_day.strftime('%d.%m.%Y %H:%M %Z')}"
    )
