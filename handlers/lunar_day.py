
from datetime import datetime, timedelta
import ephem
import pytz  # Убедитесь, что эта библиотека установлена
import os

# Проверяем текущую рабочую директорию
print(f"Текущая рабочая директория: {os.getcwd()}")

# Замените на ваш часовой пояс, например, 'Europe/Moscow'
timezone = pytz.timezone('Europe/Moscow')

def load_lunar_descriptions(filename):
    descriptions = {}
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                key, value = line.strip().split(':', 1)
                descriptions[int(key)] = value.strip().replace('\\n', '\n')


    except FileNotFoundError:
        print(f"Ошибка: файл {filename} не найден.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    return descriptions

# Загружаем лунные описания
lunar_descriptions = load_lunar_descriptions('handlers/lunar_descriptions.txt')

def get_lunar_day_and_end_time():
    # Получаем текущее время с учетом часового пояса
    now = datetime.now(timezone)
    moon = ephem.Moon()
    moon.compute(now)

    last_new_moon = ephem.previous_new_moon(now)

    # Переводим last_new_moon в нужный часовой пояс
    last_new_moon_utc = last_new_moon.datetime().replace(tzinfo=pytz.utc).astimezone(timezone)

    delta_days = (now - last_new_moon_utc).days

    lunar_day = (delta_days % 29) + 1

    # Время окончания текущего лунного дня с учетом часового пояса
    end_of_lunar_day = last_new_moon_utc + timedelta(days=delta_days + 1)

    return lunar_day, end_of_lunar_day

async def lunar_day_command(update, context):
    lunar_day, end_of_lunar_day = get_lunar_day_and_end_time()

    # Получаем описание текущего лунного дня
    description = lunar_descriptions.get(lunar_day, 'Описание не найдено.')

    response = (
        f"Сейчас продолжается {lunar_day} лунный день. \n\n{description} \n\n"
        f"Время окончания {lunar_day}-го лунного дня: {end_of_lunar_day.strftime('%d.%m.%Y %H:%M %Z')}"
    )

    await update.message.reply_text(response)



# библиотека pip install ephem
# pip install pytz

