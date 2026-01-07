from __future__ import annotations

import random
import re
from pathlib import Path

from core.actions import OutPhoto, OutText

from .state import get_today_card_for_user, set_today_card_for_user


# Триггеры можно расширять по мере надобности
TAROT_TRIGGERS = [
    "карта дня",
    "карту дня",
    "карте дня",
    "таро",
    "совет",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    """Формат файла:
    image1.jpg|Описание...
    image2.jpg|Описание...

    Также поддерживаем старый формат `image1.jpg|...` и `image1.jpg : ...`.
    """
    path = _descriptions_file()
    if not path.exists():
        return {}

    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # допускаем разделители | или :
        if "|" in line:
            name, desc = line.split("|", 1)
        elif ":" in line:
            name, desc = line.split(":", 1)
        else:
            continue

        name = name.strip()
        desc = desc.strip().replace("\\n", "\n")
        if name:
            out[name] = desc
    return out


def _pick_random_card(available: list[str]) -> str:
    return random.choice(available)


def get_tarot_day_reply(text: str, user_id: int, source: str = ""):
    ...
    """Карта дня:
    - По триггеру выбирает случайную карту (картинка + описание).
    - Одному пользователю — только 1 раз в сутки.
    - При повторном запросе в тот же день — сообщает, что уже выдавал.
    """
    if not _triggered(text):
        return None

    # 1) проверяем лимит на пользователя
    already = get_today_card_for_user(user_id=user_id, source=source)
    if already is not None:
        return [OutText("Я уже отправлял тебе карту дня сегодня 😉 Приходи завтра!")]

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


