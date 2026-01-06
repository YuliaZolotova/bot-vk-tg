from __future__ import annotations

import logging
from typing import List

from core.types import Action, OutText, OutPhoto
from handlers.message_handler import get_keyword_reply
from utils.Tarot.tarot_advice import TarotAdvice
from handlers.lunar_day import get_lunar_text
from utils.horoscope import detect_zodiac, get_horoscope_from_website
from utils.time_checker import is_time_request, get_time_reply

logger = logging.getLogger(__name__)
tarot_advice = TarotAdvice()

async def build_reply_actions(text: str, user_id: int, chat_id: int) -> List[Action]:
    """Возвращает список действий (текст/фото). Если действий нет — вернёт пустой список (бот молчит)."""
    low = (text or "").lower().strip()
    out: List[Action] = []

    try:
        # 2) Карта дня (фото + описание)
        tarot_triggers = ["карта дня", "карту дня", "карте дня", "совет", "таро"]
        if any(k in low for k in tarot_triggers):
            advice = tarot_advice.get_daily_advice(user_id)
            if isinstance(advice, dict):
                out.append(OutPhoto(path=advice["image"], caption=""))
                out.append(OutText(text=advice["description"]))
            else:
                out.append(OutText(text=str(advice)))
            return out

        # 3) Лунный день
        if any(k in low for k in ["лунный день", "лунные сутки", "луна"]):
            out.append(OutText(text=get_lunar_text()))
            return out

        # 4) Гороскоп
        if "гороскоп" in low:
            sign = low.split("гороскоп", 1)[1].strip()
            zodiac = detect_zodiac(sign)
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

        # Ничего не нашли — молчим
        return out

    except Exception:
        # На ошибках тоже лучше молчать, но лог оставить
        logger.exception("build_reply_actions failed")
        return []

