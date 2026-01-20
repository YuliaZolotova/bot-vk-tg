from __future__ import annotations

import random
import re
from pathlib import Path

from core.actions import OutPhoto, OutText

from .state import get_today_card_for_user, reset_today_card_for_user, set_today_card_for_user


# Триггеры можно расширять по мере надобности
TAROT_TRIGGERS = [
    "карта дня",
    "карту дня",
    "карте дня",
    "таро",
    "совет",
]

# Команда для тестирования: сбросить ТОЛЬКО свою статистику по "карте дня",
# чтобы можно было запросить карту повторно в тот же день.
# Работает и в TG и в VK (потому что привязка идёт к source + user_id).
TAROT_RESET_TRIGGERS = {
    "/tarot_reset",
    "/reset_tarot",
    "сброс карты дня",
    "сбросить карту дня",
    "сброс карты таро",
    "сбросить карту таро",
}


def _images_dir() -> Path:
    # Папка с картинками: modules/tarot_day/images
    return Path(__file__).resolve().parent / "images"


def _descriptions_file() -> Path:
    # Текстовый файл с описаниями: modules/tarot_day/descriptions.txt
    return Path(__file__).resolve().parent / "descriptions.txt"


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _triggered(text: str) -> bool:
    low = _normalize(text)
    return any(t in low for t in TAROT_TRIGGERS)


def _load_descriptions() -> dict[str, str]:
    """Читает descriptions.txt с поддержкой переносов строк.

    ✅ РЕКОМЕНДУЕМЫЙ формат (многострочный):
        image1.jpg|Первая строка
        Вторая строка

        Третий абзац (пустая строка выше сохранится)

        image2.jpg|...

    То есть:
      - новая запись начинается со строки "imageX.jpg|" (или "imageX.jpg:"),
      - все следующие строки до следующего "imageY..." относятся к этому описанию,
      - пустые строки сохраняются (будут абзацы).

    Также поддерживаем старый однострочный формат и литералы "\\n".
    """
    path = _descriptions_file()
    if not path.exists():
        return {}

    out: dict[str, str] = {}
    current_name: str | None = None
    buf: list[str] = []

    def _flush():
        nonlocal current_name, buf
        if not current_name:
            return
        text = "\n".join(buf).strip("\n").replace("\\n", "\n")
        if text:
            out[current_name] = text
        current_name = None
        buf = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        # важно: не .strip(), чтобы не уничтожать пустые строки (абзацы)
        line = raw_line.rstrip("\n")

        # комментарии пропускаем (но только если это отдельная строка)
        if line.strip().startswith("#"):
            continue

        # новая запись? (image*.jpg| ... или image*.png: ...)
        head = line.split("|", 1)[0].split(":", 1)[0].strip()
        is_new = bool(re.match(r"^image\d+\.(jpg|jpeg|png)$", head, re.IGNORECASE)) and ("|" in line or ":" in line)

        if is_new:
            _flush()
            if "|" in line:
                name, first = line.split("|", 1)
            else:
                name, first = line.split(":", 1)
            current_name = name.strip()
            buf = [first.lstrip()]  # первый кусок описания
            continue

        # продолжение текущего описания
        if current_name is not None:
            buf.append(line)

    _flush()
    return out


def _pick_random_card(available: list[str]) -> str:
    return random.choice(available)


def get_tarot_day_reply(text: str, user_id: int, source: str = ""):
    """Карта дня:
    - По триггеру выбирает случайную карту (картинка + описание).
    - Одному пользователю — только 1 раз в сутки.
    - При повторном запросе в тот же день — сообщает, что уже выдавал.

    + Команда для тестирования: сбросить свою статистику.
    """
    if not text:
        return None

    # 0) Команда тестирования: сбросить свою статистику по карте дня
    low = _normalize(text)
    if low in TAROT_RESET_TRIGGERS:
        cleared = reset_today_card_for_user(user_id=user_id, source=source)
        if cleared:
            return [OutText("✅ Сбросила твою статистику по «карте дня». Можешь запросить карту снова 🙂")]
        return [OutText("ℹ️ У тебя и так нет записи о карте на сегодня. Просто попроси «карту дня».")]

    if not _triggered(text):
        return None

    # 1) проверяем лимит на пользователя
    already = get_today_card_for_user(user_id=user_id, source=source)
    if already is not None:
        already_responses = [
            "Эй, полегче 😄 Карта дня уже была. Вселенная на сегодня высказалась, следующая — только завтра 🔮",
            "Я бы рад, но карты сегодня уже всё сказали 😏 Завтра будет новое предсказание ✨",
            "Вторую карту сегодня не выдаём — гадание по расписанию 😄 Следующая завтра",
            "Осторожно, перерасход магии! ✨ На сегодня лимит исчерпан, приходи завтра 🔮",
            "Вселенная сказала: «Хватит на сегодня» 🤷‍♂️ Завтра продолжим 🔮",
        ]
        return [OutText(random.choice(already_responses))]

    # 2) собираем доступные изображения
    images_dir = _images_dir()
    if not images_dir.exists():
        return [OutText("Папка с картами не найдена (modules/tarot_day/images).")]

    image_files = sorted(
        [p.name for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    )
    if not image_files:
        return [OutText("В папке modules/tarot_day/images нет картинок.")]

    # 3) читаем описания
    descriptions = _load_descriptions()

    # 4) выбираем карту
    card = _pick_random_card(image_files)
    set_today_card_for_user(user_id=user_id, source=source, card_filename=card)

    # 5) строим ответ
    img_path = str((images_dir / card).resolve())
    desc = descriptions.get(card) or descriptions.get(card.lower())
    if not desc:
        # fallback: ищем по номеру image12.jpg -> 12
        m = re.match(r"^image(\d+)\.(jpg|jpeg|png)$", card, re.IGNORECASE)
        if m:
            key_num = f"image{m.group(1)}.jpg"
            desc = descriptions.get(key_num, "")

    if desc:
        return [OutPhoto(path=img_path, caption=""), OutText(desc)]
    return [OutPhoto(path=img_path, caption=""), OutText("Описание для этой карты не найдено.")]
