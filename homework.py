import logging
from http import HTTPStatus
import os
import json
import requests
import sys
import telegram
import time
from traceback import format_exc

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
handler.setLevel(logging.DEBUG)
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
        if 'Сбой' in message:
            logger.info('FAILURE message sending')
            return
        logger.info('STATUS message sending')
    except Exception as error:
        logger.exception(error)
        raise


def get_api_answer(current_timestamp) -> dict:
    """Makes a request to API -> converts API answer to python."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    # По заданию я должен логировать это - я создал исключения для различных
    # ситуаций и далее при срабатывании исключения - оно автоматически будет
    # логироваться для меня - именно то, которое сработало + тк я прописал в
    # классах исключений суть случившейся проблемы - это описание будет
    # передано в лог как раз при вызове данного исключения -
    # и мне не нужно прописывать под каждым событием его логировние
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise ApiNotFoundError
        if response.status_code != HTTPStatus.OK:
            raise ApiConnectionFailed(response.status_code)
        return response.json()
    except (Exception, json.decoder.JSONDecodeError) as error:
        logger.exception(error)
        raise


def check_response(response) -> list:
    """Checking API answer."""
    # Тут у меня такая же мысль, как описал выше - ко мне приходит ответ:
    # в блоке try  - я по логике событий сначала проверяю в правильном ли
    # формате пришел запрос,
    # далее если формат подошел - есть ли там нужные ключ,
    # далее если ключа нет делаю возврат пустого списка (так просят в задании),
    # далее я извлекаю сам ключ и проверяю подходит ли нам формат его значения
    # и если все в порядке я возвращаю результат.
    # При этом, как только в любом из вышеперечисленных пунктов сработает
    # заготовленное исключение - оно сразу будет передано в обработку
    # и будет создан его лог (на основании описания в классе исключения),
    # поэтому я обернул все эти события в try -
    # потому что при любом из них будет обработано исключение + залогировано
    try:
        if not isinstance(response, dict):
            raise ResponseNotDictError(response)
        if 'homeworks' not in response:
            raise KeyNotExistsError('homeworks')
        # В задании указано, что функция должна возвращать пустой список,
        # тут мы его и возвращаем, а потом уже проверяем его статус в функции
        # проверки статусов. Хотя эту проверку сразу можно сделать и в данной
        # функции, но она отвечает за проверку структуры ответа, поэтому,
        # тут я проверку не делаю, а просто возвращаю пустой список
        # и не вызываю исключений.
        if not response['homeworks']:
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
    # Тут я руководствовался такой же логикой как описал выше,
    # если так делать плохая практака тогда мне следует
    # обрабатывать + логировать в таком виде как написано ниже
    # или я что-то упускаю:

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

    # Возможно я что-то не так понимаю и нам не нужно все логировать,
    # что обрабатывается исключениями и наоборот,
    # но у нас ведь все обрабатываемые исключения относятся к классу ERROR -
    # поэтому мы должны лоигровать их все, исходя из нашего ДЗ
    # и если не выводить все эти условия, которые могут могут привести
    # к некорректной работе модуля в блок try -
    # тогда нужно будет прописавать под каждым условий
    # его обработку и логирование,
    # что повлечет большее кол-во повторяющегося кода
    # или как еше можно это реализовать?

    if not homework:
        message = 'No new statuses from Master'
        logger.debug(message)
        return
    try:
        if 'homework_name' not in homework:
            raise KeyNotExistsError('homework_name')
        if 'status' not in homework:
            raise KeyNotExistsError('status')
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            raise HomeworkStatusError(homework_status)
    except Exception as error:
        logger.exception(error)
        raise
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checks the availability of env variables."""
    # Если есть возможность - просьба присылать ссылку на источник,
    # который поясняет, почему строчка кода ниже работает в данной функции,
    # тк при проверке тестами - функция возвращает мне значение последней
    # переменной, а не True/False
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
            message = f'Сбой в работе программы:{error} {format_exc()}'
            if message != error_filter:
                error_filter = message
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
