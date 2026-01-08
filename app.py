from fastapi import FastAPI, Request, Response
from core.engine import build_reply_actions
from adapters.vk_sender import send_actions_vk
from adapters.tg_sender import send_actions_tg
from settings import VK_CONFIRMATION, VK_SECRET, TG_WEBHOOK_SECRET

app = FastAPI()

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
        from_id = msg.get("from_id", 0)

        actions = await build_reply_actions(text, int(from_id), int(peer_id), source="vk")
        if peer_id and actions:
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

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    actions = await build_reply_actions(text, user_id, chat_id, source="tg")
    if actions:
        send_actions_tg(chat_id, actions)

    return {"ok": True}
