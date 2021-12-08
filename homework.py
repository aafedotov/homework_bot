import os
import time
import requests
import logging

import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='main.log',
    filemode='w'
)

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение через Telegram API."""
    if check_tokens():
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    else:
        logging.error('Проблемы с токенами!')
        return 'Нет токенов'


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту API Яндекс.Домашка."""
    if check_tokens():
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        try:
            api_answer = requests.get(ENDPOINT,
                                      headers=HEADERS,
                                      params=params)
            return api_answer.json()
        except Exception as error:
            logging.error(f'Ошибка при запросе к основному API: {error}')
            return error
    logging.error('Проблемы с токенами!')
    return 'Нет токенов'


def check_response(response):
    """Проверяем ответ API на корректность."""
    if type(response) == dict:
        return response.get('homeworks')
    logging.error('Невалидный ответ от API')
    return None


def parse_status(homework):
    """Извлекаем статус домашки и возвращаем читабельную строку."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, все ли токены доступны из env."""
    return bool(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.info('Нет ничего нового')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()
