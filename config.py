import os

def env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value if value is not None else default

# Telegram
TG_TOKEN = env("TG_TOKEN")
TG_WEBHOOK_SECRET = env("TG_WEBHOOK_SECRET")  # put a random string, used in /tg/<secret>

# VK
VK_TOKEN = env("VK_TOKEN")
VK_CONFIRMATION = env("VK_CONFIRMATION")      # from VK Callback "confirmation string"
VK_SECRET = env("VK_SECRET")                  # set in VK Callback settings and in Render env
