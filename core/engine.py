from __future__ import annotations
from typing import List
from core.types import Action, OutText, OutPhoto
from handlers.message_handler import get_keyword_reply
from utils.Tarot.tarot_advice import TarotAdvice
from handlers.lunar_day import get_lunar_text
from utils.horoscope import detect_zodiac, get_horoscope_from_website
from utils.time_checker import is_time_request, get_time_reply

tarot_advice = TarotAdvice()

async def build_reply_actions(text: str, user_id: int, chat_id: int) -> List[Action]:
    low = (text or "").lower().strip()
    out: List[Action] = []

    # 2) Карта дня (фото + описание)
    tarot_triggers = ["карта дня", "карту дня", "карте дня", "совет", "таро"]
    if any(k in low for k in tarot_triggers):
        advice = tarot_advice.get_daily_advice(user_id)
        if isinstance(advice, dict):
            if advice.get("image"):
                out.append(OutPhoto(path=advice["image"], caption=""))
            out.append(OutText(text=advice.get("description", "")))
        else:
            out.append(OutText(text=str(advice)))
        return out

    # 3) Лунный день
    if any(k in low for k in ["лунный день", "лунные сутки", "луна"]):
        out.append(OutText(text=get_lunar_text()))
        return out

    # 4) Гороскоп
    if "гороскоп" in low:
        zodiac = detect_zodiac(low)
        if zodiac:
            out.append(OutText(text=get_horoscope_from_website(zodiac)))
        else:
            out.append(OutText(text="Хочешь гороскоп? Напиши: 'гороскоп для овна' (или другой знак)."))
        return out

    # 5) Время
    if is_time_request(low):
        out.append(OutText(text=get_time_reply()))
        return out

    # 1) Обычные ответы по ключевым словам
    reply = get_keyword_reply(low)
    if reply:
        out.append(OutText(text=reply))
        return out

    out.append(OutText(text="Не понял 🙃 Напиши: карта дня / лунный день / гороскоп для <знак> / время"))
    return out
