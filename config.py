import os

# VK
VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_SECRET = os.getenv("VK_SECRET", "")          # must match "Секретный ключ" in VK Callback settings
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION", "")

# Telegram
TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_WEBHOOK_SECRET = os.getenv("TG_WEBHOOK_SECRET", "")  # used in URL /tg/<secret>

# Misc
TZ = os.getenv("TZ", "Europe/Moscow")
