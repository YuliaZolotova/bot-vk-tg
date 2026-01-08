from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.actions import OutText

# Приближённый расчёт по синодическому месяцу
SYNODIC_MONTH_DAYS = 29.530588853
REFERENCE_NEW_MOON_UTC = datetime(2000, 1, 6, 18, 14)  # UTC (опорное новолуние)

TRIGGERS_MAIN = {"лунный день", "лунные сутки", "луна", "лунник"}
TRIGGERS_EXTRA = {"лунный день подробно", "лунный день подробнее", "лунные сутки подробно", "лунные сутки подробнее"}


def _moon_phase_name(age_days: float) -> str:
    q = SYNODIC_MONTH_DAYS / 4.0
    if age_days < 1.0 or age_days > SYNODIC_MONTH_DAYS - 1.0:
        return "Новолуние (около)"
    if abs(age_days - SYNODIC_MONTH_DAYS / 2.0) < 1.0:
        return "Полнолуние (около)"
    if abs(age_days - q) < 0.8:
        return "Первая четверть"
    if abs(age_days - 3 * q) < 0.8:
        return "Последняя четверть"
    if age_days < SYNODIC_MONTH_DAYS / 2.0:
        return "Растущая Луна"
    return "Убывающая Луна"


def _read_kv_file(path: str) -> dict[int, str]:
    """
    Читает файлы формата:
      <num>|<text>
    """
    out: dict[int, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "|" not in line:
                    continue
                k, v = line.split("|", 1)
                k = k.strip()
                v = v.strip()
                try:
                    out[int(k)] = v
                except ValueError:
                    continue
    except FileNotFoundError:
        return {}
    return out


def _compute_lunar(now_local: datetime) -> dict:
    """
    Возвращает:
    - lunar_day: int (1..30)
    - start_local, end_local
    - phase_name
    - next_new_local, next_full_local
    """
    now_utc = now_local.astimezone(ZoneInfo("UTC"))
    ref = REFERENCE_NEW_MOON_UTC.replace(tzinfo=ZoneInfo("UTC"))

    delta_days = (now_utc - ref).total_seconds() / 86400.0
    age = delta_days % SYNODIC_MONTH_DAYS  # возраст луны в сутках

    lunar_day = int(age) + 1
    # чтобы 30-е не вылезало слишком часто в приближении
    if lunar_day == 30 and age < 29.0:
        lunar_day = 29

    # “начало лунного дня” приближенно = момент, когда age перешёл целую границу
    start_utc = now_utc - timedelta(days=(age - int(age)))
    end_utc = start_utc + timedelta(days=1)

    # ближайшее новолуние: age -> 0
    days_to_new = (SYNODIC_MONTH_DAYS - age) % SYNODIC_MONTH_DAYS
    next_new_utc = now_utc + timedelta(days=days_to_new)

    # ближайшее полнолуние: age -> SYNODIC/2
    full_age = SYNODIC_MONTH_DAYS / 2.0
    days_to_full = (full_age - age) % SYNODIC_MONTH_DAYS
    next_full_utc = now_utc + timedelta(days=days_to_full)

    return {
        "lunar_day": lunar_day,
        "start_local": start_utc.astimezone(now_local.tzinfo),
        "end_local": end_utc.astimezone(now_local.tzinfo),
        "phase_name": _moon_phase_name(age),
        "next_new_local": next_new_utc.astimezone(now_local.tzinfo),
        "next_full_local": next_full_utc.astimezone(now_local.tzinfo),
    }


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m %H:%M")


def _format_extra(raw: str) -> str:
    """
    raw формат:
    Работа=...;Общение=...;Семья=...;Здоровье=...;Сад=...;Сны=...
    Возвращает красивый текст блоками.
    """
    # распарсим в словарь
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    m = {}
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        m[k.strip().lower()] = v.strip()

    def get(key: str) -> str:
        return m.get(key, "Пока нет информации.")

    # Важно: стиль как ты просила
    return (
        "Работа/бизнес/новые дела.\n"
        f"{get('работа')}\n\n"
        "Общение.\n"
        f"{get('общение')}\n\n"
        "Семейные дела.\n"
        f"{get('семья')}\n\n"
        "Питание, здоровье.\n"
        f"{get('здоровье')}\n\n"
        "Сад, огород.\n"
        f"{get('сад')}\n\n"
        "Сновидения.\n"
        f"{get('сны')}"
    )


def get_lunar_day_reply(text: str, tz_name: str = "Europe/Moscow"):
    if not text:
        return None

    t = text.strip().lower()

    is_main = t in TRIGGERS_MAIN
    is_extra = t in TRIGGERS_EXTRA
    if not is_main and not is_extra:
        return None

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    data = _compute_lunar(now)
    lunar_day = data["lunar_day"]

    short_map = _read_kv_file("modules/lunar_day/lunar_short.txt")
    extra_map = _read_kv_file("modules/lunar_day/lunar_extra.txt")

    if is_extra:
        raw = extra_map.get(lunar_day)
        if not raw:
            return [OutText("📌 Подробной информации для этого лунного дня пока нет. (Добавь строку в lunar_extra.txt)")]
        return [OutText(_format_extra(raw))]

    # main
    short_desc = short_map.get(lunar_day, "Описание для этого дня пока не заполнено.")

    msg = (
        f"🌙 Сейчас: {lunar_day}-е лунные сутки\n"
        f"Начало: {_fmt_dt(data['start_local'])}\n"
        f"Окончание: {_fmt_dt(data['end_local'])}\n"
        f"\n"
        f"Фаза: {data['phase_name']}\n"
        f"Ближайшее новолуние: {_fmt_dt(data['next_new_local'])}\n"
        f"Ближайшее полнолуние: {_fmt_dt(data['next_full_local'])}\n"
        f"\n"
        f"Коротко о дне: {short_desc}\n\n"
        "📌 Хочешь подробнее? Напиши: Лунный день подробно\n\n"
        "ℹ️ Расчёт выполнен по московскому времени и может быть приближённым."
    )
    return [OutText(msg)]
