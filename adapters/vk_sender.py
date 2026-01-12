import time
import random
import requests

from core.actions import OutText, OutPhoto
from settings import VK_TOKEN, TYPING_DELAY_MIN, TYPING_DELAY_MAX

VK_API_VERSION = "5.199"


def _typing_delay() -> None:
    """
    Небольшая пауза, чтобы бот выглядел "живым" (как будто печатает).
    Время берётся из settings: TYPING_DELAY_MIN / TYPING_DELAY_MAX
    """
    time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))


def _vk_call(method: str, params: dict, timeout: int = 20) -> dict:
    """
    Универсальный вызов VK API.
    - method: например "messages.send"
    - params: параметры метода
    Возвращает поле response, либо бросает исключение, если VK вернул error.
    """
    params = dict(params)
    params["access_token"] = VK_TOKEN
    params["v"] = VK_API_VERSION

    r = requests.post(f"https://api.vk.com/method/{method}", data=params, timeout=timeout)
    data = r.json()

    if "error" in data:
        raise RuntimeError(f"VK API error in {method}: {data['error']}")

    return data["response"]


def _vk_upload_message_photo(peer_id: int, file_path: str) -> str:
    """
    Загружает картинку в сообщения VK и возвращает строку attachment вида:
    photo{owner_id}_{photo_id}_{access_key}
    """
    # 1) Получаем upload URL для сообщений
    server = _vk_call("photos.getMessagesUploadServer", {"peer_id": peer_id})
    upload_url = server["upload_url"]

    # 2) Загружаем файл на upload URL
    with open(file_path, "rb") as f:
        up_resp = requests.post(upload_url, files={"photo": f}, timeout=30)
        up = up_resp.json()

    # Проверка, что VK вернул нужные поля
    if not all(k in up for k in ("photo", "server", "hash")):
        raise RuntimeError(f"VK upload response missing fields: {up}")

    # 3) Сохраняем загруженное фото
    saved = _vk_call(
        "photos.saveMessagesPhoto",
        {"photo": up["photo"], "server": up["server"], "hash": up["hash"]},
    )[0]

    owner_id = saved["owner_id"]
    photo_id = saved["id"]
    access_key = saved.get("access_key")

    attachment = f"photo{owner_id}_{photo_id}"
    if access_key:
        attachment += f"_{access_key}"

    return attachment


def _make_random_id(seed: int, idx: int) -> int:
    """
    Главная защита от дублей в VK.

    VK НЕ будет показывать повторно сообщение, если повторная отправка идёт
    с тем же random_id.

    Поэтому:
    - для ответов на входящее сообщение используем seed = conversation_message_id (или id)
      -> тогда при ретраях VK получит тот же random_id и НЕ сделает дубль.
    - для рассылок/админских сообщений seed обычно нет -> используем случайный random_id
    """
    if seed:
        # "стабильный" random_id из seed и номера action в списке
        # чтобы если actions несколько, у каждого был свой rid, но стабильный на ретраях
        return (int(seed) % 1_000_000_000) * 10 + (idx + 1)

    # для рассылок/админа (нет входящего message id) делаем случайный
    return random.randint(1, 2_000_000_000)


def send_actions_vk(peer_id: int, actions, seed: int = 0) -> None:
    """
    Отправляет actions в VK.

    ВАЖНОЕ ПРО ДУБЛИ:
    - VK может прислать одно и то же входящее событие несколько раз (ретраи).
    - Чтобы бот НЕ отправлял дубль, random_id должен быть одинаковым при повторе.
    - Для этого мы принимаем seed (например conversation_message_id) и делаем random_id из seed.

    ПРО КАРТУ ДНЯ:
    - раньше было: фото иногда падало -> VK ретраил -> модуль уже записал "карта выдана"
      и пользователь видел отказ.
    - теперь: даже если VK ретраит, random_id будет тот же -> дублей не будет,
      и пользователь не получит повтор/лишние сообщения.
    - если фото не отправилось, мы пытаемся отправить fallback-текст.
    """
    if not actions:
        return

    # 1) "печатает..." (не критично, если сломается)
    try:
        requests.post(
            "https://api.vk.com/method/messages.setActivity",
            data={
                "access_token": VK_TOKEN,
                "v": VK_API_VERSION,
                "peer_id": int(peer_id),
                "type": "typing",
            },
            timeout=10,
        )
    except Exception:
        pass

    # 2) задержка печати (не критично)
    try:
        _typing_delay()
    except Exception:
        pass

    # 3) отправка действий
    for idx, action in enumerate(actions):
        rid = _make_random_id(seed, idx)

        try:
            # --- отправка фото ---
            if isinstance(action, OutPhoto):
                attachment = _vk_upload_message_photo(int(peer_id), action.path)
                _vk_call(
                    "messages.send",
                    {
                        "peer_id": int(peer_id),
                        "random_id": rid,
                        "message": action.caption or "",
                        "attachment": attachment,
                    },
                )
                continue

            # --- отправка текста ---
            if isinstance(action, OutText):
                _vk_call(
                    "messages.send",
                    {
                        "peer_id": int(peer_id),
                        "random_id": rid,
                        "message": action.text,
                    },
                )
                continue

            # если когда-нибудь появятся другие action-типы
            _vk_call(
                "messages.send",
                {
                    "peer_id": int(peer_id),
                    "random_id": rid,
                    "message": str(action),
                },
            )

        except Exception:
            # НЕ ПАДАЕМ наружу, чтобы VK не ретраил webhook бесконечно.
            # Пытаемся отправить fallback-текст (это спасает "карту дня" и подобные модули)
            try:
                _vk_call(
                    "messages.send",
                    {
                        "peer_id": int(peer_id),
                        "random_id": _make_random_id(seed, idx + 1000),
                        "message": (
                            "⚠️ Не получилось отправить картинку (это особенность ВК), "
                            "но вот текст:"
                        ),
                    },
                )
            except Exception:
                pass

            # продолжаем дальше, чтобы не потерять остальные OutText из списка actions
            continue
