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


def _today_msk():
    return datetime.now(ZoneInfo(TZ_NAME)).date()


def _is_group_chat(platform: str, chat_id: int) -> bool:
    """
    TG: группы/супергруппы имеют chat_id < 0
    VK: беседы имеют peer_id >= 2000000000
    """
    try:
        chat_id = int(chat_id)
    except Exception:
        return False

    if platform == "tg":
        return chat_id < 0
    if platform == "vk":
        return chat_id >= 2000000000
    return False


def _extract_title(text: str) -> str | None:
    """
    Возвращает:
      - None, если нет триггера "кто сегодня"
      - "" (пусто), если есть "кто сегодня" но дальше ничего
      - строку титула (например "кот", "главный по мемам")
    """
    low = (text or "").lower()
    m = WHO_RE.search(low)
    if not m:
        return None

    start = m.end()
    tail = (text[start:] or "").strip()

    # убираем "у нас", "в чате", "тут" и похожее в начале хвоста
    tail_low = tail.lower()
    for junk in ["у нас", "в чате", "тут", "сейчас", "вообще", "то"]:
        if tail_low.startswith(junk + " "):
            tail = tail[len(junk):].strip()
            tail_low = tail.lower()



    # убираем "?" "!" "." и т.п. в конце
    tail = TRAIL_PUNCT_RE.sub("", tail).strip()

    # ограничим длину, чтобы не вставляли простыни
    if len(tail) > 60:
        tail = tail[:60].rstrip()

    return tail


def _read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = []
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
            return lines
    except FileNotFoundError:
        return []


def _format_name(platform: str, user_id: int, display_name: str | None) -> str:
    if platform == "tg":
        if display_name:
            return display_name
        return f"пользователь {user_id}"

    # VK: если имени нет — кликабельный формат
    if display_name:
        return display_name
    return f"[id{user_id}|пользователь {user_id}]"


def _pg_funcs():
    """
    Берём функции из core.chat_store_pg.
    Если база недоступна — модуль просто не сломает бота.
    """
    try:
        from core.chat_store_pg import (
            init_who_today_tables,
            get_available_users_for_today,
            assign_title_today,
        )
        return init_who_today_tables, get_available_users_for_today, assign_title_today
    except Exception:
        return None


def get_who_today_reply(text: str, platform: str, chat_id: int, user_id: int):
    if not text:
        return None

    low = text.strip().lower()

    # ---------- статистика по титулу в этом чате ----------
    if low in {"/who_stats", "кто сегодня статистика", "статистика кто сегодня", "статистика титулов"}:
        if not _is_group_chat(platform, chat_id):
            return [OutText("📊 Статистика доступна только в групповых чатах/беседах.")]

        try:
            from core.chat_store_pg import get_who_today_title_stats
            top = get_who_today_title_stats(platform, chat_id, limit=10)
        except Exception:
            return [OutText("📊 Не получилось получить статистику (ошибка базы).")]

        if not top:
            return [OutText("📊 Статистики пока нет — ещё никто не получал титулы 🙂")]

        lines = ["📊 Топ титулов в этом чате (за всё время):", ""]
        for title, cnt in top:
            lines.append(f"• {title} — {cnt}")
        return [OutText("\n".join(lines))]


    title = _extract_title(text)
    if title is None:
        return None  # нет "кто сегодня"

    # ✅ ВАЖНО: модуль работает только в группах/беседах
    if not _is_group_chat(platform, chat_id):
        return [OutText("🎭 Это работает только в групповых чатах/беседах. Добавь меня в беседу и напиши: «кто сегодня кот» 🙂")]

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
        candidates_all = get_users(platform, chat_id, day, limit=200)
    except Exception:
        return [OutText("😕 Не получилось получить список участников для этого чата.")]

    # если вообще никого не знаем (обычно: бот только что добавлен/после деплоя)
    if not candidates_all:
        return [OutText("🙂 Я пока не знаю участников этого чата. Пусть несколько людей напишут любые сообщения — и попробуй ещё раз.")]

    # 🔥 Правило “не назначать самому себе” — только если есть выбор
    candidates = [(uid, nm) for (uid, nm) in candidates_all if int(uid) != int(user_id)]
    if not candidates:
        # если кроме автора никого нет — назначаем автору (иначе всегда будет “раздал”)
        candidates = candidates_all

    # если всё равно пусто (на всякий случай)
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

    # вторая строка — подпор
    tails = _read_lines("modules/who_today/tails.txt")
    if tails:
        msg = msg + "\n" + random.choice(tails)

    # подсказка про статистику
    msg = (
            msg
            + "\n\n📊 Хочешь статистику? Напиши: Статистика титулов или отправь команду /who_stats"
    )

    return [OutText(msg)]


