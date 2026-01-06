import logging
logger = logging.getLogger(__name__)

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

# Reuse your existing modules
from utils.Tarot.tarot_advice import TarotAdvice
from handlers.romeo import romeo_keywords, reply_to_romeo_question
from handlers.shine import shine_keywords, gadalka_keywords, reply_to_shine_question
from handlers.lunar_day import get_lunar_day_text
from utils.horoscope import get_horoscope_from_website

# This one is Telegram-shaped (Update/Context), so we call it through fakes
from handlers.message_handler import reply_to_message as tg_style_reply_to_message


@dataclass
class OutText:
    text: str


@dataclass
class OutSticker:
    file_id: str  # Telegram sticker file_id


@dataclass
class OutPhoto:
    path: str     # local path inside the project
    caption: str = ""


OutAction = Union[OutText, OutSticker, OutPhoto]


_tarot = TarotAdvice()


class _FakeChat:
    def __init__(self, chat_id: int):
        self.id = chat_id


class _FakeMessage:
    def __init__(self, text: str, chat_id: int):
        self.text = text
        self.chat = _FakeChat(chat_id)
        self._out: List[OutAction] = []

    async def reply_text(self, text: str):
        self._out.append(OutText(text=text))

    async def reply_photo(self, photo):
        # Not used by message_handler.py, but keep for safety
        self._out.append(OutText(text="(photo)"))

    @property
    def out(self) -> List[OutAction]:
        return self._out


class _FakeUpdate:
    def __init__(self, text: str, chat_id: int):
        self.message = _FakeMessage(text=text, chat_id=chat_id)
        self.effective_chat = _FakeChat(chat_id)


class _FakeBot:
    def __init__(self, out: List[OutAction]):
        self._out = out

    async def send_sticker(self, chat_id: int, sticker: str):
        # sticker here is usually a Telegram file_id
        self._out.append(OutSticker(file_id=sticker))


class _FakeContext:
    def __init__(self, out: List[OutAction]):
        self.bot = _FakeBot(out)


async def build_reply_actions(text: str, user_id: int, chat_id: int) -> list[OutAction]:
    """Единая логика ответов (VK + Telegram).

    На вход получаем только текст и идентификаторы, на выход — список действий:
    OutText / OutPhoto.
    """
    low = (text or "").lower().strip()
    out: list[OutAction] = []

    # --- КАРТА ДНЯ / ТАРО ---
    tarot_triggers = ["карта дня", "карту дня", "карте дня", "совет", "таро"]
    if any(k in low for k in tarot_triggers):
        advice = tarot_advice.get_daily_advice(user_id)
        if isinstance(advice, dict):
            out.append(OutPhoto(path=advice["image"], caption=""))
            out.append(OutText(text=advice["description"]))
        else:
            out.append(OutText(text=str(advice)))
        return out

    # --- ЛУННЫЙ КАЛЕНДАРЬ ---
    if any(k in low for k in ["лунный день", "лунные сутки", "луна"]):
        out.append(OutText(text=get_lunar_day_text()))
        return out

    # --- ГОРОСКОП ---
    if "гороскоп" in low:
        sign = low.split("гороскоп", 1)[1].strip()

        zodiac_signs = {
            "овен": ["овен", "овна", "овну", "овнов", "овнам"],
            "телец": ["телец", "тельца", "тельцу", "тельцов", "тельцам"],
            "близнецы": ["близнецы", "близнеца", "близнецу", "близнецов", "близнецам"],
            "рак": ["рак", "рака", "раку", "раков", "ракам"],
            "лев": ["лев", "льва", "льву", "львов", "львам"],
            "дева": ["дева", "девы", "деве", "девам", "дев"],
            "весы": ["весы", "весов", "весам"],
            "скорпион": ["скорпион", "скорпиона", "скорпиону", "скорпионам"],
            "стрелец": ["стрелец", "стрельца", "стрельцу", "стрельцам"],
            "козерог": ["козерог", "козерога", "козерогу", "козерогам"],
            "водолей": ["водолей", "водолея", "водолею", "водолеям"],
            "рыбы": ["рыбы", "рыбе", "рыбам", "рыб"],
        }

        found_sign = None
        for zodiac, forms in zodiac_signs.items():
            if any(form in sign for form in forms):
                found_sign = zodiac
                break

        if found_sign:
            out.append(OutText(text=get_horoscope_from_website(found_sign)))
        else:
            out.append(OutText(text="Хочешь гороскоп? Напиши: Гороскоп для ... Кого?\nЯ ж вас всех не упомню 😁"))
        return out

    # --- РОМЕО ---
    if any(k in low for k in romeo_keywords):
        question = low
        if "ромео" in low:
            question = low.split("ромео", 1)[1].strip()
        out.append(OutText(text=reply_to_romeo_question(question)))
        return out

    # --- SHINE / ГАДАЛКА ---
    if any(k in low for k in (shine_keywords + gadalka_keywords)):
        if any(k in low for k in shine_keywords):
            question = low
            if "шайн" in low:
                question = low.split("шайн", 1)[1].strip()
            out.append(OutText(text=reply_to_shine_question(question)))
            return out
        if any(k in low for k in gadalka_keywords):
            out.append(OutText(text="Гадай - не гадай... одна фигня получится 😅"))
            return out

    # --- ФОЛБЭК (старый TG-стиль message_handler) ---
    # Он может генерировать любые OutText/OutPhoto через FakeUpdate.
    try:
        more = await tg_style_reply_to_message(text=text, user_id=user_id, chat_id=chat_id)
        out.extend(more)
    except Exception:
        logger.exception("Fallback handler failed")
        out.append(OutText(text="Что-то пошло не так 😅 Попробуй ещё раз."))

    return out
