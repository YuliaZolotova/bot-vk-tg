import re
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.actions import OutText

# Строго HH:MM
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

# Фразы для НЕ админской статистики/обычных людей — тут не нужно,
# это отдельная фича, поэтому только для ангельского времени:

FORMAT_ERROR_REPLIES = [
    "❗ Формат времени неверный. Напиши вот так: 11:11",
    "⛔ Я понимаю только формат HH:MM. Пример: 11:11",
    "⌛ Немного не так. Время нужно писать вот так: 11:11",
]

OTHER_TIME_REPLIES = [
    "⏰ Не не не... Сейчас другое время: {now}",
    "🕰 Сейчас на часах {now}, Хочешь меня запутать?",
    "⌚ Не ври! Сейчас {now}.",
]

NO_MEANING_REPLIES = [
    "🤷 Это время ничего не значит.",
    "😌 Для этого времени нет особого значения.",
    "✨ Иногда время — просто время. Здесь без знаков.",
]

# Команды статистики
MY_STATS_TRIGGERS = {
    "мое ангельское время",
    "моё ангельское время",
    "мои зеркальные цифры",
    "/my_angel_time",
}


def _now_dt(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def _load_meanings() -> dict[str, str]:
    """
    Читает modules/angel_time/times.txt
    Формат: HH:MM|Текст
    """
    path = "modules/angel_time/times.txt"
    meanings: dict[str, str] = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" not in line:
                    continue
                k, v = line.split("|", 1)
                k = k.strip()
                v = v.strip()
                if _TIME_RE.match(k) and v:
                    meanings[k] = v
    except FileNotFoundError:
        return {}

    return meanings


def _is_time_close(user_time: str, now: datetime, tolerance_minutes_after: int = 1) -> bool:
    """
    Засчитываем:
    - если сейчас ровно HH:MM
    - или если сейчас на 1 минуту позже (например 11:12 за 11:11)
    """
    try:
        hh, mm = user_time.split(":")
        base = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    except Exception:
        return False

    if now.strftime("%H:%M") == base.strftime("%H:%M"):
        return True

    for i in range(1, tolerance_minutes_after + 1):
        if now.strftime("%H:%M") == (base + timedelta(minutes=i)).strftime("%H:%M"):
            return True

    return False


# ---- Статистика через Postgres (если подключено) ----

def _pg_getters():
    """
    Аккуратно пробуем подключить функции из Postgres.
    Если Postgres не настроен — вернём None и модуль не упадёт.
    """
    try:
        from core.chat_store_pg import init_angel_time_stats, log_angel_time, get_user_angel_stats  # noqa
        return init_angel_time_stats, log_angel_time, get_user_angel_stats
    except Exception:
        return None


def get_angel_time_reply(
    text: str,
    platform: str,
    chat_id: int,
    user_id: int,
    tz_name: str = "Europe/Moscow",
):
    """
    Возвращает список actions или None.

    Реагирует на:
    - "Мое ангельское время" / "Мои зеркальные цифры" -> статистика (если Postgres подключен)
    - строгое время HH:MM
    - неправильный формат вида 11.11 / 11-11 -> подсказка про формат
    """
    if not text:
        return None

    t = text.strip()
    lower = t.lower().strip()

    # 1) Команда статистики
    if lower in MY_STATS_TRIGGERS:
        pg = _pg_getters()
        if not pg:
            return [OutText("📊 Статистика пока недоступна (Postgres не подключен).")]

        init_stats, _log, get_stats = pg
        # Таблица создаётся, если её нет
        try:
            init_stats()
        except Exception:
            return [OutText("📊 Не получилось открыть статистику (ошибка базы).")]

        try:
            total, top = get_stats(platform, chat_id, user_id, limit=5)
        except Exception:
            return [OutText("📊 Не получилось получить статистику (ошибка базы).")]

        if total == 0:
            return [OutText("📊 У тебя пока нет статистики. Поймай время типа 11:11 и напиши его 🙂")]

        lines = [f"📊 Твоя статистика (в этом чате): всего попаданий — {total}", ""]
        lines.append("Топ времени:")
        for tv, cnt in top:
            lines.append(f"• {tv} — {cnt} раз")
        return [OutText("\n".join(lines))]

    # 2) Неверный формат, но похоже на время (11.11, 11-11, 11:1 и т.п.)
    # Требование: принимаем ТОЛЬКО 11:11. Остальное — ошибка формата.
    if re.match(r"^\d{1,2}[.\-:]\d{1,2}$", t) and not _TIME_RE.match(t):
        return [OutText(random.choice(FORMAT_ERROR_REPLIES))]

    # 3) Если не строго HH:MM — не реагируем (пусть другие модули отвечают)
    if not _TIME_RE.match(t):
        return None

    now = _now_dt(tz_name)
    now_str = now.strftime("%H:%M")

    # 4) Если сейчас другое время (и не попали в +1 минуту)
    if not _is_time_close(t, now, tolerance_minutes_after=1):
        reply = random.choice(OTHER_TIME_REPLIES).format(now=now_str)
        return [OutText(reply)]

    # 5) Сейчас совпало (или +1 мин) -> ищем значение
    meanings = _load_meanings()

    if t in meanings:
        # Логируем статистику, только если подключен Postgres
        pg = _pg_getters()
        if pg:
            init_stats, log_time, _get_stats = pg
            try:
                init_stats()
                log_time(platform, chat_id, user_id, t)
            except Exception:
                # статистика не критична, не ломаем ответ
                pass

        hint = "\n\n📊 Хочешь свою статистику? Напиши: Мое ангельское время или введи команду /my_angel_time"
        return [OutText(meanings[t] + hint)]

    # 6) Значения нет, но время совпало
    return [OutText(random.choice(NO_MEANING_REPLIES))]
