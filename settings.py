import os

ANGEL_TIME_TZ = os.getenv("ANGEL_TIME_TZ", "Europe/Moscow")


VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_SECRET = os.getenv("VK_SECRET", "")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION", "")

TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_WEBHOOK_SECRET = os.getenv("TG_WEBHOOK_SECRET", "")

# --- typing imitation ---
TYPING_DELAY_MIN = 3
TYPING_DELAY_MAX = 6


ADMIN_TG_IDS = os.getenv("ADMIN_TG_IDS", "")  # например "123,456"
ADMIN_VK_IDS = os.getenv("ADMIN_VK_IDS", "")  # например "111,222"

