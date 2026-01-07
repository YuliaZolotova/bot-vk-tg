from core.actions import OutText
from core.idle_notifier import get_known_chats, get_group_chats
from settings import ADMIN_TG_IDS, ADMIN_VK_IDS
from adapters.tg_sender import send_actions_tg
from adapters.vk_sender import send_actions_vk


def _parse_admin_ids(raw: str) -> set[int]:
    raw = (raw or "").strip()
    if not raw:
        return set()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    out = set()
    for p in parts:
        try:
            out.add(int(p))
        except ValueError:
            pass
    return out


ADMIN_TG = _parse_admin_ids(ADMIN_TG_IDS)
ADMIN_VK = _parse_admin_ids(ADMIN_VK_IDS)


def _is_admin(platform: str, from_id: int) -> bool:
    if platform == "tg":
        return from_id in ADMIN_TG
    if platform == "vk":
        return from_id in ADMIN_VK
    return False


def _send_to_targets(targets: list[tuple[str, int]], text: str) -> tuple[int, int]:
    actions = [OutText(text=text)]
    sent_vk = 0
    sent_tg = 0

    for plat, chat_id in targets:
        if plat == "tg":
            send_actions_tg(chat_id, actions)
            sent_tg += 1
        elif plat == "vk":
            send_actions_vk(chat_id, actions)
            sent_vk += 1

    return sent_vk, sent_tg


def handle_admin_command(platform: str, from_id: int, text: str):
    """
    Возвращает OutText(...) как ответ в текущий чат (например "ок, отправлено"),
    или None если это не команда/не админ.
    """
    if not text:
        return None

    t = text.strip()

    # команды только для админа
    if not _is_admin(platform, from_id):
        return None

    # --- /all текст ---
    if t.startswith("/all "):
        msg = t[len("/all "):].strip()
        targets = get_known_chats()  # все: лички + группы
        vk, tg = _send_to_targets(targets, msg)
        return OutText(f"✅ Отправлено: VK={vk}, TG={tg}, всего={vk+tg}")

    # --- /groups текст ---
    if t.startswith("/groups "):
        msg = t[len("/groups "):].strip()
        targets = get_group_chats()  # только группы
        vk, tg = _send_to_targets(targets, msg)
        return OutText(f"✅ В группы: VK={vk}, TG={tg}, всего={vk+tg}")

    # --- /tg текст ---
    if t.startswith("/tg "):
        msg = t[len("/tg "):].strip()
        targets = get_known_chats("tg")
        vk, tg = _send_to_targets(targets, msg)
        return OutText(f"✅ В Telegram: {tg}")

    # --- /vk текст ---
    if t.startswith("/vk "):
        msg = t[len("/vk "):].strip()
        targets = get_known_chats("vk")
        vk, tg = _send_to_targets(targets, msg)
        return OutText(f"✅ В VK: {vk}")

    # --- /send tg -100... текст /send vk 2000... текст ---
    if t.startswith("/send "):
        # формат: /send <tg|vk|tg_user|vk_user> <id> <text>
        parts = t.split(" ", 3)
        if len(parts) < 4:
            return OutText("❗ Формат: /send <tg|vk|tg_user|vk_user> <id> <текст>")

        kind = parts[1].strip()
        id_str = parts[2].strip()
        msg = parts[3].strip()

        try:
            chat_id = int(id_str)
        except ValueError:
            return OutText("❗ id должен быть числом")

        if kind == "tg":
            _send_to_targets([("tg", chat_id)], msg)
            return OutText("✅ Отправлено в TG чат")

        if kind == "vk":
            _send_to_targets([("vk", chat_id)], msg)
            return OutText("✅ Отправлено в VK чат")

        if kind == "tg_user":
            # ВАЖНО: пользователь должен был нажать Start у бота
            _send_to_targets([("tg", chat_id)], msg)
            return OutText("✅ Попыталась отправить пользователю TG (если он запускал бота)")

        if kind == "vk_user":
            _send_to_targets([("vk", chat_id)], msg)
            return OutText("✅ Попыталась отправить пользователю VK (если разрешены сообщения)")

        return OutText("❗ kind должен быть: tg | vk | tg_user | vk_user")

    return None
