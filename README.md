# Multi-platform bot: Telegram + VK (single codebase)

## What runs on Render
One web service with 2 webhooks:
- VK Callback:  /vk
- Telegram webhook: /tg/<TG_WEBHOOK_SECRET>

## Environment variables (Render -> Environment)
Telegram:
- TG_TOKEN
- TG_WEBHOOK_SECRET   (any long random string)

VK:
- VK_TOKEN
- VK_CONFIRMATION     (from VK Callback settings)
- VK_SECRET           (set the same in VK Callback server settings)

## Start command (Render)
Build:  pip install -r requirements.txt
Start:  gunicorn -k uvicorn.workers.UvicornWorker webapp:app

## Local run
python -m uvicorn webapp:app --reload --port 8000
