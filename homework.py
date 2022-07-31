import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ExceptionIsThrown
from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(stream=sys.stdout),
              logging.FileHandler('hw.log', encoding='UTF-8')]
)

logger = logging.getLogger(__name__)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Oтправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except telegram.error.TelegramError:
        logger.error('Ошибка при отправке сообщения')
        raise ExceptionIsThrown('Что пошло не так :(')


def get_api_answer(current_timestamp):
    """Запрос API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        json_response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if json_response.status_code != HTTPStatus.OK:
            logger.error('API-сервис не доступен')
            raise Exception('Ошибка при запросе к основному API')
    except requests.ConnectionError:
        logger.error(' запрос не сработал')
        raise ExceptionIsThrown('Что пошло не так :(')
    try:
        response = json_response.json()
    except Exception as error:
        logger.error(f'Неудалось преобразовать{error}')
        raise ExceptionIsThrown('Что пошло не так :(')

    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных!')
    if 'homeworks' not in response:
        raise TypeError('В сроваре нету ключа homeworks')
    if 'current_date' not in response:
        raise TypeError('В словаре нету ключа current_date')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('В словаре нету ключа homeworks!')
    
    return homeworks


def parse_status(homework):
    """Получем статус работы."""
    if 'homework_name' not in homework:
        logger.error('Нет такого ключа homework_name')
    if 'status' not in homework:
        logger.error('Нет такого ключа status')
    homework_status = homework['status']
    homework_name = homework['homework_name']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise KeyError('Неверный статус!')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical('Токены отсутствуют')
        sys.exit(0)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                time.sleep(RETRY_TIME)
                old_message = parse_status(homeworks[0])
                if old_message != message:
                    send_message(bot, message)
                else:
                    logger.info(f'Одинаковые сообщения {message}')
                current_timestamp = response['current_date']
            else:
                logger.info('домашек нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)
            same_message = message
            if same_message != message:
                logger.info(f'{message}')
                send_message(bot, message)
            else:
                logger.info(f'Одинаковые сообщения {message}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
