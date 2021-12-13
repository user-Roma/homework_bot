import logging
from http import HTTPStatus
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv

from exceptions import (
    ApiNotFoundError, ApiConnectionFailed, HomeworksNotListError,
    KeyNotExistsError, ResponseNotDictError, HomeworkStatusError,
    CheckTokensError
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MANDATORY_ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s.%(funcName)s: %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


RETRY_TIME = 555
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Sends a message to Telegram chat."""
    if message is None:
        return
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info('Successful message sending')
    except Exception as error:
        logger.exception(error)
        raise


def get_api_answer(current_timestamp) -> dict:
    """Makes a request to API -> converts API answer to python."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    # не совсем понял комметарий про проверку статуса, с 404 я делаю проверку
    # не упал ли сервер и вызываю исключение, в случае когда он упал или тут
    # нужно полностью убрать сам вызов исключения и делать только лог?
    try:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise ApiNotFoundError
    # тут оставляем вызов исключения?
        if response.status_code != HTTPStatus.OK:
            raise ApiConnectionFailed(response.status_code)
    # какое тут может случиться исключение?
        return response.json()
    except Exception as error:
        logger.exception(error)
        raise


def check_response(response) -> list:
    """Checking API answer."""
    # подскажите, как тогда луче оформить,
    # чтобы не писать вывод в лог в каждо из условий?
    # Может у вас ест ссылка на пример?
    # Потому что, как я вижу, это будет:

    # if not isinstance(response, dict):
    #     logger.exception(ResponseNotDictError(response))
    #     raise ResponseNotDictError(response)
    # if 'homeworks' not in response:
    #     logger.exception(KeyNotExistsError('homeworks'))
    #     raise KeyNotExistsError('homeworks')
    # if not response['homeworks']:
    #     return
    # homework = response.get('homeworks')
    # if not isinstance(homework, list):
    #     logger.exception(HomeworksNotListError(homework))
    #     raise HomeworksNotListError(homework)
    # return homework[0]

    try:
        if not isinstance(response, dict):
            raise ResponseNotDictError(response)
        if 'homeworks' not in response:
            raise KeyNotExistsError('homeworks')
        if not response['homeworks']:
            return
        homework = response.get('homeworks')
        if not isinstance(homework, list):
            raise HomeworksNotListError(homework)
        return homework[0]
    except Exception as error:
        logger.exception(error)
        raise


def parse_status(homework) -> str:
    """Generate message for sending."""
    try:
        if not homework:
            message = 'No new statuses from Master'
            logger.debug(message)
            return
        if 'homework_name' not in homework:
            raise KeyNotExistsError('homework_name')
        if 'status' not in homework:
            raise KeyNotExistsError('status')
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            raise HomeworkStatusError(homework_status)
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logger.exception(error)
        raise


def check_tokens() -> bool:
    """Checks the availability of env variables."""
    # Можно сразу вернуть результат return a and b and c:
    # это не вернет False в случае отсутствия последней переменной,
    # как просят по условии - не пойму как это работает?
    # мои тесты этот вариант не проходит..
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main() -> None:
    """The bot logic."""
    if not check_tokens():
        for var in MANDATORY_ENV_VARS:
            if var not in os.environ:
                logger.critical(CheckTokensError(var))
                raise CheckTokensError(var)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    error_filter = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response['current_date']
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != error_filter:
                error_filter = message
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
