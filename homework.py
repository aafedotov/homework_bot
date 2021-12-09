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
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Cообщение {message} успешно отправлено.')
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение: {message}. Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту API Яндекс.Домашка."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    global is_api_error
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    api_answer = requests.get(ENDPOINT,
                              headers=HEADERS,
                              params=params)
    if api_answer.status_code != 200:
        if not is_api_error:
            message = f'Ошибка при запросе к API.'
            send_message(bot, message)
            is_api_error = True
        logging.error(message)
        raise message
    is_api_error = False
    return api_answer.json()


def check_response(response):
    """Проверяем ответ API на корректность."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    global is_api_error
    if type(response) == dict:
        if 'homeworks' in response:
            result = response['homeworks']
            if type(result) == list:
                is_api_error = False
                return response['homeworks']
            message = 'homeworks извлечен из API не в виде списка'
            if not is_api_error:
                send_message(bot, message)
                is_api_error = True
            logging.error(message)
            raise message
        message = 'В полученном от API результате нет ожидаемого ключа'
        if not is_api_error:
            send_message(bot, message)
            is_api_error = True
        logging.error(message)
        raise message
    message = 'Невалидный ответ от API'
    if not is_api_error:
        send_message(bot, message)
        is_api_error = True
    logging.error(message)
    raise message


def parse_status(homework):
    """Извлекаем статус домашки и возвращаем читабельную строку."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    global is_api_error
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_status:
        raise 'Отсутствует ключ homework status'
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        is_api_error = False
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        message = f'Получен незадокументированный статус работы:{homework_status}'
        if not is_api_error:
            send_message(bot, message)
            is_api_error = True
        logging.error(message)
        raise error


def check_tokens():
    """Проверяем, все ли токены доступны из env."""
    if not TELEGRAM_TOKEN:
        logging.error('Проблема с токеном API Telegram')
    if not TELEGRAM_CHAT_ID:
        logging.error('Проблема с CHAT_ID')
    if not PRACTICUM_TOKEN:
        message = 'Проблема с токеном API Яндекс'
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            send_message(bot, message)
        logging.error(message)
    return bool(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while check_tokens():
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
