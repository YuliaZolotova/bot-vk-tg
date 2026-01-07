from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TarotDailyState:
    date: str  # YYYY-MM-DD (UTC)
    card: str  # filename, e.g. image12.jpg


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _state_path() -> Path:
    # project_root/ data/ tarot_day_state.json
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "tarot_day_state.json"


def _load_raw() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        # если файл повредился — начнем с чистого
        return {}


def _save_raw(data: dict[str, Any]) -> None:
    path = _state_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _user_key(user_id: int, source: str) -> str:
    source = str(source or "").strip().lower() or "unknown"
    return f"{source}:{int(user_id)}"


def get_today_card_for_user(user_id: int, source: str) -> TarotDailyState | None:
    """Возвращает карту пользователя на сегодня, если уже выдавали."""
    raw = _load_raw()
    key = _user_key(user_id, source)
    rec = raw.get(key)
    if not isinstance(rec, dict):
        return None
    if rec.get("date") != _today_utc():
        return None
    card = rec.get("card")
    if not isinstance(card, str) or not card:
        return None
    return TarotDailyState(date=rec["date"], card=card)


def set_today_card_for_user(user_id: int, source: str, card_filename: str) -> TarotDailyState:
    raw = _load_raw()
    key = _user_key(user_id, source)
    state = TarotDailyState(date=_today_utc(), card=card_filename)
    raw[key] = {"date": state.date, "card": state.card}
    _save_raw(raw)
    return state
