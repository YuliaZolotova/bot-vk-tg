from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

# Reuse your existing modules
from utils.Tarot.tarot_advice import TarotAdvice
from handlers.romeo import romeo_keywords, reply_to_romeo_question
from handlers.shine import shine_keywords, gadalka_keywords, reply_to_shine_question
from handlers.lunar_day import lunar_day_command
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


async def build_reply_actions(*, text: str, user_id: int, chat_id: int) -> List[OutAction]:
    """
    Platform-neutral entrypoint.
    Returns a list of actions: text / sticker / photo.
    """
    t = (text or "").strip()
    if not t:
        return []

    low = t.lower()
    out: List[OutAction] = []

    # /start (Telegram command) or "start" alike
    if low in ("/start", "start"):
        out.append(OutText(text="Привет! Я бот. Напиши сообщение — я отвечу 🙂"))
        return out

    # Tarot
    if "таро" in low:
        advice = _tarot.get_daily_advice(user_id)
        if isinstance(advice, dict):
            out.append(OutPhoto(path=advice["image"], caption=advice["description"]))
        else:
            out.append(OutText(text=str(advice)))
        return out

    # Romeo
    if any(k in low for k in romeo_keywords):
        out.append(OutText(text=reply_to_romeo_question()))
        return out

    # Shine / gadalka
    if any(k in low for k in shine_keywords) or any(k in low for k in gadalka_keywords):
        out.append(OutText(text=reply_to_shine_question()))
        return out

    # Lunar day (your handler returns text)
    if "лун" in low and ("день" in low or "календар" in low):
        out.append(OutText(text=lunar_day_command()))
        return out

    # Horoscope: very simple parse like in your Telegram bot
    if "гороскоп" in low:
        # try to detect zodiac sign in text
        zodiac_signs = {
            "овен": ["овен", "овна", "овну", "овном"],
            "телец": ["телец", "тельца", "тельцу", "тельцом"],
            "близнецы": ["близнец", "близнецы", "близнецам", "близнецов"],
            "рак": ["рак", "рака", "раку", "раком"],
            "лев": ["лев", "льва", "льву", "львом"],
            "дева": ["дева", "девы", "деве", "девой", "девою"],
            "весы": ["весы", "весам", "весов"],
            "скорпион": ["скорпион", "скорпиона", "скорпиону", "скорпионом"],
            "стрелец": ["стрелец", "стрельца", "стрельцу", "стрельцом"],
            "козерог": ["козерог", "козерога", "козерогу", "козерогом"],
            "водолей": ["водолей", "водолея", "водолею", "водолеем"],
            "рыбы": ["рыбы", "рыбам", "рыб"],
        }
        found = None
        for zodiac, forms in zodiac_signs.items():
            if any(f in low for f in forms):
                found = zodiac
                break
        if found:
            out.append(OutText(text=get_horoscope_from_website(found)))
        else:
            out.append(OutText(text="Хочешь гороскоп? Напиши: Гороскоп для ... Кого? \nЯ ж вас всех не упомню 😁"))
        return out

    # Fallback: your big keyword responder (Telegram-shaped) via fakes
    fake_update = _FakeUpdate(text=t, chat_id=chat_id)
    fake_context = _FakeContext(out=out)
    await tg_style_reply_to_message(fake_update, fake_context)
    # It may have added to update.message.out too, merge:
    out.extend(fake_update.message.out)

    # Deduplicate: keep order, remove empty texts
    cleaned: List[OutAction] = []
    for a in out:
        if isinstance(a, OutText) and not a.text:
            continue
        cleaned.append(a)
    return cleaned
