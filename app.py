from fastapi import FastAPI, Request, Response

from core.engine import build_reply_actions
from adapters.vk_sender import send_actions_vk
from adapters.tg_sender import send_actions_tg

from core.idle_notifier import touch, init_known_chats
from settings import VK_CONFIRMATION, VK_SECRET, TG_WEBHOOK_SECRET

from core.chat_store_pg import init_who_today_tables, touch_chat_user


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    # Загружаем сохранённые чаты (Render Postgres), чтобы рассылка помнила их после деплоя
    await init_known_chats()

    # Таблицы для модуля "Кто сегодня"
    init_who_today_tables()


@app.get("/")
def health():
    return {"ok": True}


@app.post("/vk")
async def vk_callback(req: Request):
    data = await req.json()

    if VK_SECRET and data.get("secret") != VK_SECRET:
        return Response("forbidden", status_code=403)

    t = data.get("type")
    if t == "confirmation":
        return Response(VK_CONFIRMATION)

    if t == "message_new":
        msg = data.get("object", {}).get("message", {})
        text = msg.get("text", "")

        peer_id = msg.get("peer_id")
        if not peer_id:
            return Response("ok")
        peer_id = int(peer_id)

        from_id_raw = (
            msg.get("from_id")
            or msg.get("user_id")
            or msg.get("sender_id")
            or 0
        )
        try:
            from_id = int(from_id_raw)
        except (TypeError, ValueError):
            from_id = 0

        # запоминаем чат для рассылок
        touch("vk", peer_id)

        # запоминаем пользователя в этом чате для "Кто сегодня"
        if from_id > 0:
            touch_chat_user("vk", peer_id, from_id, None)

        # важно: не допускаем vk:0
        if from_id <= 0:
            return Response("ok")

        actions = await build_reply_actions(text, from_id, peer_id, source="vk")
        if actions:
            send_actions_vk(peer_id, actions)

    return Response("ok")


@app.post("/tg/{secret}")
async def tg_webhook(secret: str, req: Request):
    if TG_WEBHOOK_SECRET and secret != TG_WEBHOOK_SECRET:
        return Response("forbidden", status_code=403)

    data = await req.json()
    message = data.get("message") or data.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = int(message["chat"]["id"])

    # запоминаем чат для рассылок
    touch("tg", chat_id)

    user_id = int(message["from"]["id"])
    text = message.get("text", "")

    # имя для "Кто сегодня"
    tg_name = (
        (message["from"].get("first_name") or "") + " " + (message["from"].get("last_name") or "")
    ).strip()
    if not tg_name:
        tg_name = message["from"].get("username")

    # запоминаем пользователя в этом чате
    touch_chat_user("tg", chat_id, user_id, tg_name)

    actions = await build_reply_actions(text, user_id, chat_id, source="tg")
    if actions:
        send_actions_tg(chat_id, actions)

    return {"ok": True}
