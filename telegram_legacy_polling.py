
# main
import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from constants import TOKEN
from handlers.start_handler import start
from handlers.message_handler import reply_to_message as handle_message
from utils.Tarot.tarot_advice import TarotAdvice
from handlers.romeo import romeo_keywords, reply_to_romeo_question
from handlers.shine import shine_keywords, reply_to_shine_question, gadalka_keywords
from handlers.lunar_day import lunar_day_command

from utils.horoscope import get_horoscope_from_website  # Импортируйте функцию



logging.basicConfig(level=logging.INFO)

tarot_advice = TarotAdvice()

async def typing_action(update: Update):
    await update.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(5)

async def send_image_to_user(update: Update, image_path: str):
    await typing_action(update)
    try:
        await update.message.reply_photo(photo=open(image_path, 'rb'))
    except Exception as e:
        logging.error(f"Не удалось отправить изображение: {e}")
        await update.message.reply_text("Не удалось отправить изображение.")

async def send_text_to_user(update: Update, text: str):
    if text:
        await typing_action(update)
        await update.message.reply_text(text)

async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("reply_to_message вызван.")
    await typing_action(update)
    response = await handle_message(update, context)
    if response:
        await typing_action(update)
        await update.message.reply_text(response)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.lower()
    user_id = update.message.from_user.id

    if any(keyword in message_text for keyword in ["карта дня", "карту дня", "карте дня", "совет", "таро"]):
        advice = tarot_advice.get_daily_advice(user_id)
        if isinstance(advice, dict):
            await send_image_to_user(update, advice['image'])
            await send_text_to_user(update, advice['description'])
        else:
            await send_text_to_user(update, "Эй, Бро! Я сегодня уже давал совет... Завязывай! Нафиг оно надо так часто... Давай завтра глянем 😁")

    elif any(phrase in message_text for phrase in ["лунный день", "лунные сутки", "луна"]):
        await lunar_day_command(update, context)

    elif any(keyword in message_text for keyword in romeo_keywords):
        question = message_text.split("ромео")[-1].strip()
        response = await reply_to_romeo_question(question)
        await send_text_to_user(update, response)

    elif any(keyword in message_text for keyword in shine_keywords + gadalka_keywords):
        if any(keyword in message_text for keyword in shine_keywords):
            question = message_text.split("шайн")[-1].strip()
            response = await reply_to_shine_question(question)
            await send_text_to_user(update, response)
        elif any(keyword in message_text for keyword in gadalka_keywords):
            question = message_text.split("гадалка")[-1].strip()
            await send_text_to_user(update, response)





    elif any(keyword in message_text for keyword in ["гороскоп"]):

        # Разделяем сообщение по слову "гороскоп" и берем текст после него
        sign = message_text.split("гороскоп")[-1].strip()

        # Словарь с формами знаков зодиака
        zodiac_signs = {
            'овен': ['овен', 'овна', 'овну', 'овнов', 'овнам'],
            'телец': ['телец', 'тельца', 'тельцу', 'тельцов', 'тельцам'],
            'близнецы': ['близнецы', 'близнеца', 'близнецу', 'близнецов', 'близнецам'],
            'рак': ['рак', 'рака', 'раку', 'раков', 'ракам'],
            'лев': ['лев', 'льва', 'льву', 'львов', 'львам'],
            'дева': ['дева', 'девы', 'деве', 'девам', 'дев'],
            'весы': ['весы', 'весов', 'весам'],
            'скорпион': ['скорпион', 'скорпиона', 'скорпиону', 'скорпионам'],
            'стрелец': ['стрелец', 'стрельца', 'стрельцу', 'стрельцам'],
            'козерог': ['козерог', 'козерога', 'козерогу', 'козерогам'],
            'водолей': ['водолей', 'водолея', 'водолею', 'водолеям'],
            'рыбы': ['рыбы', 'рыбе', 'рыбам', 'рыб']
        }

        # Ищем знак зодиака в сообщении
        found_sign = None
        for zodiac, forms in zodiac_signs.items():
            if any(form in sign.lower() for form in forms):
                found_sign = zodiac
                break
        if found_sign:
            horoscope = get_horoscope_from_website(found_sign)
            await send_text_to_user(update, horoscope)
        else:
            await send_text_to_user(update, "Хочешь гороскоп? Напиши: Гороскоп для ... Кого? \nЯ ж вас всех не упомню 😁")





    else:
        await reply_to_message(update, context)





def main():
    print("Токен вашего бота:", TOKEN)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    app.run_polling()



if __name__ == '__main__':
    main()

# pip install beautifulsoup4
# pip install python-telegram-bot requests



