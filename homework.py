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

is_api_error = False

def send_message(bot, message):
    """Отправляем сообщение через Telegram API."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Cообщение {message} успешно отправлено.')
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение: {message}. Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту API Яндекс.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT,
                                  headers=HEADERS,
                                  params=params)
        global.is_api_error = False
        return api_answer.json()
    except Exception as error:
        message = f'Ошибка при запросе к API: {error}'
        if not global.is_api_error:
            send_message(bot, message)
            global.is_api_error = True
        logging.error(message)
        return error


def check_response(response):
    """Проверяем ответ API на корректность."""
    if type(response) == dict:
        try:
            result = response['homeworks']
            global.is_api_error = False
            return return result
        except Exception as error:
            message = f'В полученном от API результате нет ожидаемого ключа: {error}'
            if not global.is_api_error:
                send_message(bot, message)
                global.is_api_error = True
            logging.error(message)
            return None
    message = 'Невалидный ответ от API'
    if not global.is_api_error:
        send_message(bot, message)
        global.is_api_error = True
    logging.error(message)
    return None


def parse_status(homework):
    """Извлекаем статус домашки и возвращаем читабельную строку."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        message = 'Получен незадокументированный статус работы'
        send_message(bot, message)
        logging.error(message)
        return 'Получен незадокументированный статус работы'


def check_tokens():
    """Проверяем, все ли токены доступны из env."""
    if not PRACTICUM_TOKEN:
        message = 'Проблема с токеном API Яндекс'
        send_message(bot, message)
        logging.error(message)
    if not TELEGRAM_TOKEN:
        logging.error('Проблема с токеном API Telegram')
    if not TELEGRAM_CHAT_ID:
        logging.error('Проблема с CHAT_ID')
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
                logging.debug('Нет новых статусов')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
