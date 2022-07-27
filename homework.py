import os
import logging
import sys
import time
import telegram
import requests

from dotenv import load_dotenv


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
    """ Oтправляет сообщение в Telegram чат."""
    try:
        message = 'Вам телеграмма!'
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """ Запрос API-сервиса """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response_1 = requests.get(ENDPOINT, headers=HEADERS, params=params)
    response = response_1.json()
    if response_1.status_code != 200:
        logger.error('API-сервис не доступен')
        raise Exception('Ошибка при запросе к основному API')

    return response


def check_response(response):
    """ Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных!')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('В словаре нету ключа homeworks!')
    if 'current_date' not in response.keys():
        raise TypeError('В словаре нету ключа current_date')
    if 'homeworks' not in response.keys():
        raise TypeError('В сроваре нету ключа homeworks')

    return response.get('homeworks')


def parse_status(homework):
    """ Получем статус работы!"""
    homework_name = homework['homework_name']
    if 'homework_name' not in homework:
        logger.error('Нет такого ключа homework_name')
    homework_status = homework['status']
    if 'status' not in homework:
        logger.error('Нет такого ключа status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise KeyError
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """ Проверяет доступность переменных окружения,
        которые необходимы для работы программы."""
    test_env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for tokens in test_env:
        if tokens is None:
            logger.critical(
                f'Не доступна {tokens} переменная.'
                f'Программа принудительно закрыта'
            )
            return False

    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
