import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler, Formatter

import requests
import telegram
from dotenv import load_dotenv

import exceptions

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(
    Formatter(fmt='[%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

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


def send_message_decorator(func):
    """Декоратор для защиты от дублей сообщений."""
    memo = ''

    def wrapper(bot, message):
        nonlocal memo
        if message == memo:
            pass
        else:
            memo = message
            func(bot, message)
    return wrapper


@send_message_decorator
def send_message(bot, message):
    """Отправляем сообщение через Telegram API."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Cообщение {message} успешно отправлено.')
    except exceptions.SendError as error:
        logger.error(f'Не удалось отправить сообщение:'
                     f'{message}. Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту API Яндекс.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT,
                                  headers=HEADERS,
                                  params=params)
    except exceptions.ApiNotResponse:
        raise exceptions.ApiNotResponse('Ошибка при запросе к API.')
    if api_answer.status_code != HTTPStatus.OK:
        message = 'Ошибка при запросе к API.'
        raise exceptions.ApiNotResponse(message)
    if api_answer is None:
        message = 'Пустой ответ от API.'
        raise exceptions.ApiNotResponse(message)
    return api_answer.json()


def check_response(response):
    """Проверяем ответ API на корректность."""
    if response is None:
        message = 'Получен пустой ответ от API'
        raise exceptions.ApiEmptyResponse(message)
    if not isinstance(response, dict):
        message = 'Объект не типа dict'
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'В полученном от API результате нет ключа homeworks'
        raise KeyError(message)
    result = response.get('homeworks')
    if not isinstance(result, list):
        message = 'homeworks извлечен из API не в виде списка'
        raise TypeError(message)
    return result


def parse_status(homework):
    """Извлекаем статус домашки и возвращаем читабельную строку."""
    if 'homework_name' not in homework:
        message = 'Отсутствует ключ homework name'
        raise KeyError(message)
    if 'status' not in homework:
        message = 'Отсутствует ключ homework status'
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = (f'Получен незадокументированный'
                   f' статус работы:{homework_status}')
        raise exceptions.ApiStatusNotInDocs(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, все ли токены доступны из env."""
    if not TELEGRAM_TOKEN:
        message = 'Проблема с токеном API Telegram'
        logger.critical(message)
        return False
    if not TELEGRAM_CHAT_ID:
        message = 'Проблема с CHAT_ID'
        logger.critical(message)
        return False
    if not PRACTICUM_TOKEN:
        message = 'Проблема с токеном API Яндекс'
        logger.critical(message)
        return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens():
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
                    logger.debug('Нет новых статусов')
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logger.error(message)
                send_message(bot, message)
                time.sleep(RETRY_TIME)
    else:
        raise exceptions.TokenError('Проблема с токенами!')


if __name__ == '__main__':
    main()
