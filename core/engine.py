from modules.admin_commands.handler import handle_admin_command
from modules.simple_replies.handler import get_simple_reply
from modules.tarot_day.handler import get_tarot_day_reply

from modules.angel_time.handler import get_angel_time_reply
from settings import ANGEL_TIME_TZ



async def build_reply_actions(text: str, user_id: int, chat_id: int, source: str = "unknown"):

    # 1️⃣ Проверка админа
    admin_action = handle_admin_command(source, user_id, text)
    if admin_action:
        return [admin_action]

    # 2️⃣ Ангельское время
    actions = get_angel_time_reply(
        text=text,
        platform=source,   # "tg" или "vk"
        chat_id=chat_id,
        user_id=user_id,
        tz_name=ANGEL_TIME_TZ,
    )
    if actions:
        return actions


    # 3️⃣ Карта дня
    actions = get_tarot_day_reply(text, user_id, source=source)
    if actions:
        return actions

    # 4️⃣ Простые ответы
    actions = await get_simple_reply(text, user_id, chat_id)
    return actions
