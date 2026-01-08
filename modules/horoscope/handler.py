import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from core.actions import OutText

TZ_NAME = "Europe/Moscow"

# Слово "гороскоп" — в любом месте текста
HORO_WORD_RE = re.compile(r"\bгороскоп\b", re.IGNORECASE)

# Ожидание знака после вопроса "для кого?"
_WAITING: dict[tuple[str, int, int], float] = {}
WAIT_TTL_SECONDS = 10 * 60  # 10 минут

# Канонический знак -> slug сайта
SIGN_SLUGS: dict[str, str] = {
    "овен": "oven",
    "телец": "telec",
    "близнецы": "bliznecy",
    "рак": "rak",
    "лев": "lev",
    "дева": "deva",
    "весы": "vesy",
    "скорпион": "skorpion",
    "стрелец": "strelec",
    "козерог": "kozerog",
    "водолей": "vodoley",
    "рыбы": "ryby",
}

# Канонический знак -> все формы, как может написать человек
SIGN_FORMS: dict[str, list[str]] = {
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

# форма -> канонический знак
FORM_TO_SIGN: dict[str, str] = {}
for canon, forms in SIGN_FORMS.items():
    for f in forms:
        FORM_TO_SIGN[f] = canon

# регулярка по всем формам
SIGN_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, FORM_TO_SIGN.keys()), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

ASK_TEXT = (
    "🔮 Хочешь гороскоп? Напиши, для какого знака.\n"
    "Я всех не упомню 🙂\n\n"
    "Примеры:\n"
    "• гороскоп овен\n"
    "• гороскоп деве\n"
    "• овну"
)


def _now_msk() -> datetime:
    return datetime.now(ZoneInfo(TZ_NAME))


def _cleanup_waiting():
    now = time.time()
    dead = [k for k, exp in _WAITING.items() if exp <= now]
    for k in dead:
        _WAITING.pop(k, None)


def _set_waiting(platform: str, chat_id: int, user_id: int):
    _cleanup_waiting()
    _WAITING[(platform, chat_id, user_id)] = time.time() + WAIT_TTL_SECONDS


def _is_waiting(platform: str, chat_id: int, user_id: int) -> bool:
    _cleanup_waiting()
    exp = _WAITING.get((platform, chat_id, user_id))
    if not exp:
        return False
    if exp <= time.time():
        _WAITING.pop((platform, chat_id, user_id), None)
        return False
    return True


def _clear_waiting(platform: str, chat_id: int, user_id: int):
    _WAITING.pop((platform, chat_id, user_id), None)


def _extract_sign(text: str) -> str | None:
    """
    Возвращает канонический знак (например 'дева'), если в тексте найдено
    любое слово-форма из списка.
    """
    m = SIGN_RE.search(text or "")
    if not m:
        return None
    form = m.group(1).lower()
    return FORM_TO_SIGN.get(form)


def _get_horoscope_from_website(sign_ru: str) -> str:
    """
    Тянем с abc-moon.ru/goroskop/<slug>/
    Достаём текст из div.entry-content
    """
    slug = SIGN_SLUGS[sign_ru]
    url = f"http://www.abc-moon.ru/goroskop/{slug}/"

    try:
        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CrabBroBot/1.0)",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            },
        )
    except Exception:
        return "😕 Не получилось получить гороскоп с сайта сейчас. Попробуй чуть позже."

    if r.status_code != 200:
        return "😕 Не получилось получить гороскоп с сайта сейчас. Попробуй чуть позже."

    soup = BeautifulSoup(r.text, "html.parser")
    section = soup.find("div", class_="entry-content")
    if not section:
        return "😕 Я не нашла текст гороскопа на странице."

    # удаляем ссылки, чтобы не было мусора
    for a in section.find_all("a"):
        a.decompose()

    text = "\n\n".join(section.stripped_strings).strip()
    if not text:
        return "😕 Я не нашла текст гороскопа на странице."

    # Можно отрезать вводные, начиная с "Гороскоп"
    idx = text.lower().find("гороскоп")
    if idx != -1:
        text = text[idx:].strip()

    return text


def get_horoscope_reply(text: str, platform: str, chat_id: int, user_id: int):
    """
    - если есть "гороскоп" и нет знака -> спросить знак + запомнить ожидание
    - если есть "гороскоп" и есть знак -> вернуть гороскоп
    - если мы ждали знак и пользователь написал знак -> вернуть гороскоп
    """
    if not text:
        return None

    raw = text.strip()
    lower = raw.lower()

    has_horo_word = bool(HORO_WORD_RE.search(lower))
    sign = _extract_sign(lower)

    # 1) "гороскоп" есть, знака нет -> спросить
    if has_horo_word and not sign:
        _set_waiting(platform, chat_id, user_id)
        return [OutText(ASK_TEXT)]

    # 2) мы ждали знак, и пользователь прислал знак (без слова "гороскоп")
    if sign and _is_waiting(platform, chat_id, user_id):
        _clear_waiting(platform, chat_id, user_id)
        date_str = _now_msk().strftime("%d.%m.%Y")
        horo = _get_horoscope_from_website(sign)
        return [OutText(f"🔮 Гороскоп на сегодня ({date_str}) — {sign.capitalize()}\n\n{horo}")]

    # 3) запрос вида "гороскоп деве"
    if has_horo_word and sign:
        date_str = _now_msk().strftime("%d.%m.%Y")
        horo = _get_horoscope_from_website(sign)
        return [OutText(f"🔮 Гороскоп на сегодня ({date_str}) — {sign.capitalize()}\n\n{horo}")]

    return None
