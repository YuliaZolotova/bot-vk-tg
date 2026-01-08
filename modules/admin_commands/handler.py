import asyncio
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


def _is_admin(platform: str, from_id: int) -> bool:
    admin_tg = _parse_admin_ids(ADMIN_TG_IDS)
    admin_vk = _parse_admin_ids(ADMIN_VK_IDS)

    if platform == "tg":
        return from_id in admin_tg
    if platform == "vk":
        return from_id in admin_vk
    return False


def _send_to_targets(targets: list[tuple[str, int]], text: str) -> tuple[int, int]:
    """
    ВАЖНО:
    Отправляем в фоне, чтобы webhook ответил быстро и Telegram/VK не ретраили запрос.
    Плюс дедупликация целей, чтобы один чат не получил сообщение несколько раз.
    """
    actions = [OutText(text=text)]
    sent_vk = 0
    sent_tg = 0

    # дедупликация
    seen: set[tuple[str, int]] = set()

    # если мы внутри event loop (обычно да) — шлём в фоне
    # если вдруг нет loop (редко) — отправим синхронно
    try:
        loop = asyncio.get_running_loop()
        in_loop = True
    except RuntimeError:
        loop = None
        in_loop = False

    for plat, chat_id in targets:
        key = (plat, int(chat_id))
        if key in seen:
            continue
        seen.add(key)

        if plat == "tg":
            if in_loop and loop:
                loop.create_task(asyncio.to_thread(send_actions_tg, int(chat_id), actions))
            else:
                send_actions_tg(int(chat_id), actions)
            sent_tg += 1

        elif plat == "vk":
            if in_loop and loop:
                loop.create_task(asyncio.to_thread(send_actions_vk, int(chat_id), actions))
            else:
                send_actions_vk(int(chat_id), actions)
            sent_vk += 1

    return sent_vk, sent_tg


NON_ADMIN_COMMAND_REPLIES = [
    "😄 Ахах! Хитрый ход, но нет — командовать собой я не дам.",
    "😏 Неплохая попытка, но эти команды только для админа.",
    "🤖 Я бы и рад послушаться… но полномочий у тебя маловато.",
    "😈 Ты думаешь, это так работает? Спойлер: нет.",
    "🙃 Команда красивая, но доступ запрещён.",
]


def handle_admin_command(platform: str, from_id: int, text: str):
    if not text:
        return None

    t = text.strip()

    # если это команда, но пользователь не админ — шутливый отказ
    if t.startswith("/") and not _is_admin(platform, from_id):
        import random
        return OutText(random.choice(NON_ADMIN_COMMAND_REPLIES))

    # только админ
    if not _is_admin(platform, from_id):
        return None

    # /help
    if t == "/help":
        return OutText(
            "📌 Админ-команды:\n"
            "/all <текст> — всем чатам (лички + группы)\n"
            "/all_groups <текст> — только группы/беседы\n"
            "/tg <текст> — только Telegram\n"
            "/vk <текст> — только VK\n"
            "\n"
            "/tg_<chat_id> <текст> — в конкретный TG чат\n"
            "/vk_<peer_id> <текст> — в конкретный VK чат\n"
            "/tg_user_<user_id> <текст> — пользователю TG\n"
            "/vk_user_<user_id> <текст> — пользователю VK\n"
        )

    # должна быть команда + текст
    if " " not in t:
        return None

    cmd, msg = t.split(" ", 1)
    msg = msg.strip()
    if not msg:
        return OutText("❗ После команды должен быть текст")

    # массовые рассылки
    if cmd == "/all":
        vk, tg = _send_to_targets(get_known_chats(), msg)
        return OutText(
            "✅ Отправлено во все чаты.\n"
            f"VK: {vk}\nTG: {tg}\nВсего: {vk + tg}"
        )

    if cmd == "/all_groups":
        vk, tg = _send_to_targets(get_group_chats(), msg)
        return OutText(
            "✅ Отправлено только в группы/беседы.\n"
            f"VK: {vk}\nTG: {tg}\nВсего: {vk + tg}"
        )

    if cmd == "/tg":
        _, tg = _send_to_targets(get_known_chats("tg"), msg)
        return OutText(f"✅ Отправлено в Telegram чаты: {tg}")

    if cmd == "/vk":
        vk, _ = _send_to_targets(get_known_chats("vk"), msg)
        return OutText(f"✅ Отправлено в VK чаты: {vk}")

    # конкретные чаты
    if cmd.startswith("/tg_"):
        try:
            chat_id = int(cmd[len("/tg_"):])
        except ValueError:
            return OutText("❗ Пример: /tg_-1001234567890 текст")
        _send_to_targets([("tg", chat_id)], msg)
        return OutText(f"✅ Отправлено в TG чат: {chat_id}")

    if cmd.startswith("/vk_"):
        try:
            peer_id = int(cmd[len("/vk_"):])
        except ValueError:
            return OutText("❗ Пример: /vk_2000000001 текст")
        _send_to_targets([("vk", peer_id)], msg)
        return OutText(f"✅ Отправлено в VK чат: {peer_id}")

    # пользователи
    if cmd.startswith("/tg_user_"):
        try:
            user_id = int(cmd[len("/tg_user_"):])
        except ValueError:
            return OutText("❗ Пример: /tg_user_123456789 текст")
        _send_to_targets([("tg", user_id)], msg)
        return OutText(f"✅ Отправлено пользователю TG: {user_id}")

    if cmd.startswith("/vk_user_"):
        try:
            user_id = int(cmd[len("/vk_user_"):])
        except ValueError:
            return OutText("❗ Пример: /vk_user_123456789 текст")
        _send_to_targets([("vk", user_id)], msg)
        return OutText(f"✅ Отправлено пользователю VK: {user_id}")

    return None
