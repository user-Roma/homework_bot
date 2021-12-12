import logging
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
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.info('Successful message sending')


def get_api_answer(current_timestamp) -> dict:
    """Makes a request to API -> converts API answer to python."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    try:
        if response.status_code == 404:
            raise ApiNotFoundError
        if response.status_code != 200:
            raise ApiConnectionFailed(response.status_code)
        return response.json()
    except Exception as error:
        logger.exception(error)
        raise


def check_response(response) -> list:
    """Checking API answer."""
    try:
        if not isinstance(response, dict):
            raise ResponseNotDictError(response)
        if 'homeworks' not in response:
            raise KeyNotExistsError('homeworks')
        if response['homeworks'] == []:
            return []
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
        if homework == []:
            message = 'No new statuses from Master'
            logger.debug(message)
            return
        if 'homework_name' not in homework:
            raise KeyNotExistsError('homework_name')
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
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main() -> None:
    """The bot logic."""
    if check_tokens() is False:
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
        else:
            pass


if __name__ == '__main__':
    main()
