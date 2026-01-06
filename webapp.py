from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from core.engine import build_reply_actions
from adapters.vk_sender import send_actions_vk
from adapters.tg_sender import send_actions_tg
from config import VK_CONFIRMATION, VK_SECRET, TG_WEBHOOK_SECRET

app = FastAPI()

@app.get("/")
def health():
    return {"ok": True}

@app.post("/vk")
async def vk_callback(req: Request):
    data = await req.json()

    if VK_SECRET and data.get("secret") != VK_SECRET:
        return PlainTextResponse("forbidden", status_code=403)

    t = data.get("type")

    if t == "confirmation":
        return PlainTextResponse(VK_CONFIRMATION)

    if t == "message_new":
        msg = data.get("object", {}).get("message", {})
        text = msg.get("text", "")
        peer_id = msg.get("peer_id")
        from_id = msg.get("from_id", 0)

        actions = await build_reply_actions(text=text, user_id=int(from_id or 0), chat_id=int(peer_id or 0))
        if peer_id and actions:
            send_actions_vk(int(peer_id), actions)
        return PlainTextResponse("ok")

    return PlainTextResponse("ok")

@app.post("/tg/{secret}")
async def tg_webhook(secret: str, req: Request):
    if TG_WEBHOOK_SECRET and secret != TG_WEBHOOK_SECRET:
        return PlainTextResponse("forbidden", status_code=403)

    data = await req.json()
    message = data.get("message") or data.get("edited_message")
    if not message:
        return JSONResponse({"ok": True})

    chat_id = (message.get("chat") or {}).get("id")
    user_id = (message.get("from") or {}).get("id", 0)
    text = message.get("text", "") or ""

    actions = await build_reply_actions(text=text, user_id=int(user_id or 0), chat_id=int(chat_id or 0))
    if chat_id and actions:
        send_actions_tg(int(chat_id), actions)

    return JSONResponse({"ok": True})
