from __future__ import annotations
import os
from datetime import date
from typing import Dict, List, Tuple, Any

class TarotAdvice:
    """Карта дня: одна карта в день на пользователя.
    Возвращает dict: {"image": <path>, "description": <text>} или str (если уже было сегодня).
    """

    def __init__(self):
        base_dir = os.path.dirname(__file__)
        self.advice_file = os.path.join(base_dir, "advice.txt")
        self.image_folder = os.path.join(base_dir, "images")
        self._advice_data: List[Tuple[str, str]] = self._load_advice()
        self._daily_cache: Dict[tuple[int, str], int] = {}
        self._already_sent: set[tuple[int, str]] = set()

    def _load_advice(self) -> List[Tuple[str, str]]:
        data: List[Tuple[str, str]] = []
        if not os.path.exists(self.advice_file):
            return data
        with open(self.advice_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                card, advice = line.split(":", 1)
                data.append((card.strip(), advice.strip().replace("\\n", "\n")))
        return data

    def _card_index_for_today(self, user_id: int) -> int:
        if not self._advice_data:
            return -1
        key = (int(user_id), date.today().isoformat())
        if key in self._daily_cache:
            return self._daily_cache[key]
        # стабильный выбор на день
        idx = hash(f"{user_id}:{key[1]}") % len(self._advice_data)
        self._daily_cache[key] = idx
        return idx

    def get_daily_advice(self, user_id: int) -> Any:
        idx = self._card_index_for_today(user_id)
        if idx < 0:
            return "Файл с советами Таро не найден."

        key = (int(user_id), date.today().isoformat())
        if key in self._already_sent:
            return "Эй, Бро! Я сегодня уже давал совет... Давай завтра 😁"
        self._already_sent.add(key)

        _card_name, description = self._advice_data[idx]
        image_path = os.path.join(self.image_folder, f"image{idx+1}.jpg")
        if not os.path.exists(image_path):
            return {"image": "", "description": description}
        return {"image": image_path, "description": description}
