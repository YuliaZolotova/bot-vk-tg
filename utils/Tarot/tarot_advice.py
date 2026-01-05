
import os
import random
from datetime import datetime

class TarotAdvice:
    def __init__(self):  # Исправлено на '__init__'
        self.user_requests = {}
        self.image_folder = "utils/Tarot/images/"  # Папка с изображениями
        self.advice_data = self.load_advice_data("utils/Tarot/advice.txt")

    def load_advice_data(self, file_path):
        advice_list = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():  # Проверка на пустую строку
                    image, description = line.strip().split('|')
                    advice_list.append({
                        "image": os.path.join(self.image_folder, image),
                        "description": description
                    })
        return advice_list

    def get_daily_advice(self, user_id):
        today = datetime.now().date()

        if user_id in self.user_requests:
            last_request = self.user_requests[user_id]
            if last_request == today:
                return "Вы уже запрашивали карту сегодня. Пожалуйста, попробуйте снова завтра."  # Сообщение, если запрос уже сделан

        # Выбор случайной карты
        advice = random.choice(self.advice_data)
        self.user_requests[user_id] = today  # Сохраняем дату запроса

        return advice  # Возвращать словарь совета

# Пример использования
tarot_advice = TarotAdvice()

user_id = 12345  # Пример ID пользователя
advice = tarot_advice.get_daily_advice(user_id)

if isinstance(advice, dict):  # Убедимся, что advice — это словарь
    print(f"Изображение: {advice['image']}, Совет: {advice['description']}")
else:
    print(advice)  # Если это сообщение о том, что запрос уже сделан

