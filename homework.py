import logging
import os
import time
from json import JSONDecodeError
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
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
    """Send message in chat. using TELEGRAM_CHAT_ID."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logging.error('Сообщение не отправлено')
    logging.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Send request to endpoint of API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        request = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except Exception as error:
        logging.error(f'Сбой доступа к эндпоинту. {error}')
    if request.status_code != HTTPStatus.OK:
        raise Exception('Сбой доступа к эндпоинту.')
    else:
        try:
            logging.info('get_api_answer успешно')
            return request.json()
        except JSONDecodeError as error:
            logging.error(f'Ошибка декодирования JSON-файла. {error}')


def check_response(response):
    """Check response from API."""
    if not isinstance(response, dict):
        logging.critical('В check_response пришел не словарь')
        raise TypeError('Ошибка типа данных ответа')
    else:
        if 'homeworks' in response:
            homework = response['homeworks']
            logging.info('check response успешно')
            if isinstance(homework, list):
                return homework
        else:
            raise Exception('response["homeworks"] не содержит данных.')


def parse_status(homework):
    """Extract status from information about HW."""
    homework_status = homework['status']
    homework_name = homework['homework_name']
    if homework_status not in homework:
        logging.error('Статус отсутствует')
    if homework_name not in homework:
        logging.error('Имя отсутствует')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception as error:
        logging.error(
            f'homework_name|status ключ отсутствует в словаре, ошибка {error}'
        )
    logging.info('parse_status успешно')
    return (f'Изменился статус '
            f'проверки работы "{homework_name}". {verdict}')


def check_tokens():
    """Check all tokens."""
    TOKENS = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for var in TOKENS:
        if var is None or len(str(var)) == 0:
            logging.critical(
                f'Отсутствует обязательная '
                f'переменная окружения: {var}'
                f'Программа принудительно остановлена.'
            )
            return False
    logging.info('check_tokens успешно')
    return True


def main():
    """Check all tokens."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 2629743
    statusbefore = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            check = check_response(response)
            if check:
                statusnow = parse_status(check[0])
            else:
                statusnow = 'Отсутствует работа в запрашиваемом периоде.'
            if statusbefore != statusnow:
                send_message(bot, statusnow)
                statusbefore = statusnow
                current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            logging.info('main() выполнено')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
