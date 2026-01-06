from __future__ import annotations

from datetime import datetime, timedelta
import os
import ephem
import pytz

# Часовой пояс (можно поменять при необходимости)
TIMEZONE = pytz.timezone("Europe/Moscow")


def _load_lunar_descriptions() -> dict[int, str]:
    """Читает handlers/lunar_descriptions.txt и возвращает {day: text}."""
    here = os.path.dirname(__file__)
    filename = os.path.join(here, "lunar_descriptions.txt")
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
                except ValueError:
                    continue
    except FileNotFoundError:
        # На проде не падаем, просто вернём пустой словарь
        return {}
    return descriptions


LUNAR_DESCRIPTIONS = _load_lunar_descriptions()


def get_lunar_day_and_end_time():
    # Текущее время с учётом часового пояса
    now = datetime.now(TIMEZONE)

    last_new_moon = ephem.previous_new_moon(now)

    # last_new_moon -> aware datetime в нужном TZ
    last_new_moon_dt = last_new_moon.datetime().replace(tzinfo=pytz.utc).astimezone(TIMEZONE)

    delta_days = (now - last_new_moon_dt).days
    lunar_day = (delta_days % 29) + 1

    # конец текущего лунного дня (примерно)
    end_of_lunar_day = last_new_moon_dt + timedelta(days=delta_days + 1)
    return lunar_day, end_of_lunar_day


def get_lunar_day_text() -> str:
    """Платформо-независимый текст для VK и Telegram."""
    lunar_day, end_of_lunar_day = get_lunar_day_and_end_time()
    description = LUNAR_DESCRIPTIONS.get(lunar_day, "Описание не найдено.")
    return (
        f"Сейчас продолжается {lunar_day} лунный день.\n\n{description}\n\n"
        f"Время окончания {lunar_day}-го лунного дня: {end_of_lunar_day.strftime('%d.%m.%Y %H:%M %Z')}"
    )


async def lunar_day_command(update, context):
    # Telegram-хендлер оставляем, но теперь он использует общий текст
    await update.message.reply_text(get_lunar_day_text())

