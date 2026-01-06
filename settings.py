import os

VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_SECRET = os.getenv("VK_SECRET", "")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION", "")

TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_WEBHOOK_SECRET = os.getenv("TG_WEBHOOK_SECRET", "")

TYPING_DELAY_MIN = float(os.getenv("TYPING_DELAY_MIN", "3"))
TYPING_DELAY_MAX = float(os.getenv("TYPING_DELAY_MAX", "6"))