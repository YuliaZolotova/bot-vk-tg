import requests
from bs4 import BeautifulSoup


def get_horoscope_from_website(sign: str) -> str:
    url = f"http://www.abc-moon.ru/goroskop/{sign}/"
    response = requests.get(url)
    if response.status_code != 200:
        return "Не удалось получить гороскоп. Попробуйте позже."

    soup = BeautifulSoup(response.text, 'html.parser')
    horoscope_section = soup.find('div', class_='entry-content')  # Убедитесь, что класс правильный

    if horoscope_section:
        # Удаляем ссылки
        for a in horoscope_section.find_all('a'):
            a.decompose()

        # Получаем весь текст
        text = '\n\n'.join(horoscope_section.stripped_strings)

        # Находим индекс начала текста с "Гороскоп для..."
        start_index = text.find("Гороскоп для")

        if start_index != -1:
            # Возвращаем текст начиная с "Гороскоп для..."
            return text[start_index:]

        return "Гороскоп не найден."

    return "Гороскоп не найден."


# Пример использования
sign = 'deva'  # Знак Зодиака
horoscope = get_horoscope_from_website(sign)
print(horoscope)  # Вывод гороскопа

