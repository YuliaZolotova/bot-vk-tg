from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup

# Источник: abc-moon.ru (как в исходном проекте)
_BASE = "https://abc-moon.ru/goroskop/"

_ZODIAC = {
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
    "водолей": "vodolej",
    "рыбы": "ryby",
}

_ZODIAC_FORMS = {
    "овен": ["овен", "овна", "овну", "овном", "овне"],
    "телец": ["телец", "тельца", "тельцу", "тельцом", "тельце"],
    "близнецы": ["близнецы", "близнеца", "близнецам", "близнецов", "близнецу"],
    "рак": ["рак", "рака", "раку", "раком", "раке"],
    "лев": ["лев", "льва", "льву", "львом", "льве"],
    "дева": ["дева", "девы", "деве", "девой", "дев"],
    "весы": ["весы", "весов", "весам", "весами"],
    "скорпион": ["скорпион", "скорпиона", "скорпиону", "скорпионом", "скорпионе"],
    "стрелец": ["стрелец", "стрельца", "стрельцу", "стрельцом", "стрельце"],
    "козерог": ["козерог", "козерога", "козерогу", "козерогом", "козероге"],
    "водолей": ["водолей", "водолея", "водолею", "водолеем", "водолее"],
    "рыбы": ["рыбы", "рыб", "рыбе", "рыбам", "рыбами"],
}

def detect_zodiac(text: str) -> str | None:
    low = (text or "").lower()
    for zodiac, forms in _ZODIAC_FORMS.items():
        if any(f in low for f in forms):
            return zodiac
    return None

def get_horoscope_from_website(zodiac: str) -> str:
    zodiac = (zodiac or "").lower().strip()
    slug = _ZODIAC.get(zodiac)
    if not slug:
        return "Не понял знак. Пример: 'гороскоп для овна'."

    url = f"{_BASE}{slug}/"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paragraphs = [re.sub(r"\s+", " ", p) for p in paragraphs if p and len(p) > 40]

        if not paragraphs:
            return "Не смог найти текст гороскопа на странице."

        text = max(paragraphs, key=len)
        return f"Гороскоп для {zodiac}:\n\n{text}"
    except Exception as e:
        return f"Не получилось получить гороскоп (ошибка: {e})."
