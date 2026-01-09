import random
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from core.actions import OutText

TZ_NAME = "Europe/Moscow"

# ловим "кто сегодня" где угодно
WHO_RE = re.compile(r"(?:^|[\s,!.?])кто\s+сегодня\b", re.IGNORECASE)

# удалим мусор в конце титула
TRAIL_PUNCT_RE = re.compile(r"[?!.,:;]+$")


def _read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = []
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                lines.append(s)
            return lines
    except FileNotFoundError:
        return []


def _today_msk():
    return datetime.now(ZoneInfo(TZ_NAME)).date()


def _extract_title(text: str) -> str | None:
    """
    Берём всё, что после "кто сегодня".
    Примеры:
      "бро, кто сегодня кот?" -> "кот"
      "бот, а кто сегодня у нас главный по мемам?" -> "главный по мемам"
    """
    low = (text or "").lower()

    m = WHO_RE.search(low)
    if not m:
        return None

    # берём хвост после найденного "кто сегодня"
    start = m.end()
    tail = (text[start:] or "").strip()

    # чистим начало от служебных слов
    # например: "у нас", "в чате", "тут"
    tail_low = tail.lower().strip()
    for prefix in ["у нас", "в чате", "тут", "вообще", "сейчас", "значит"]:
        if tail_low.startswith(prefix + " "):
            tail = tail[len(prefix):].strip()
            tail_low = tail.lower().strip()

    # убрать лишние знаки в конце
    tail = TRAIL_PUNCT_RE.sub("", tail).strip()

    # если человек написал "кто сегодня??" — титула нет
    if not tail:
        return ""

    # ограничим длину, чтобы не вставляли простыни
    if len(tail) > 60:
        tail = tail[:60].rstrip()

    return tail


def _format_name(platform: str, user_id: int, display_name: str | None) -> str:
    if platform == "tg":
        if display_name:
            return display_name
        return f"пользователь {user_id}"

    # VK: если имени нет — можно сделать безопасный “кликабельный” формат
    # (в беседах VK формат [id123|текст] обычно работает)
    if display_name:
        return display_name
    return f"[id{user_id}|пользователь {user_id}]"


def _pg_funcs():
    """
    Берём функции из core.chat_store_pg.
    Если база недоступна — модуль просто не сломает бота.
    """
    try:
        from core.chat_store_pg import init_who_today_tables, get_available_users_for_today, assign_title_today  # noqa
        return init_who_today_tables, get_available_users_for_today, assign_title_today
    except Exception:
        return None


def get_who_today_reply(text: str, platform: str, chat_id: int, user_id: int):
    if not text:
        return None

    title = _extract_title(text)
    if title is None:
        return None  # нет "кто сегодня"

    # если нет титула
    if title == "":
        return [OutText("😄 А кто именно? Напиши: «кто сегодня кот» или «кто сегодня главный по мемам».")]

    pg = _pg_funcs()
    if not pg:
        return [OutText("😕 Модуль «Кто сегодня» пока недоступен (Postgres не подключен).")]

    init_tables, get_users, assign = pg
    try:
        init_tables()
    except Exception:
        return [OutText("😕 Не получилось открыть базу для «Кто сегодня».")]

    day = _today_msk()

    try:
        candidates = get_users(platform, chat_id, day, limit=200)
    except Exception:
        return [OutText("😕 Не получилось получить список участников для этого чата.")]

    # не назначаем титул самому вызывающему? (по желанию)
    # если хочешь можно убрать это правило
    candidates = [(uid, nm) for (uid, nm) in candidates if int(uid) != int(user_id)]

    if not candidates:
        fallbacks = _read_lines("modules/who_today/fallbacks.txt")
        if not fallbacks:
            fallbacks = ["😄 На сегодня я уже всем раздал титулы. Завтра продолжим!"]
        return [OutText(random.choice(fallbacks))]

    chosen_id, chosen_name = random.choice(candidates)
    try:
        assign(platform, chat_id, day, chosen_id, title)
    except Exception:
        # даже если не записали — лучше ответить, чем молчать
        pass

    phrases = _read_lines("modules/who_today/phrases.txt")
    if not phrases:
        phrases = ["🎭 Сегодня {title} — {name}."]

    name = _format_name(platform, int(chosen_id), chosen_name)
    tpl = random.choice(phrases)
    msg = tpl.format(title=title, name=name)

    return [OutText(msg)]
