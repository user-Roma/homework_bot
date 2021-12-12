import requests
import time
import unittest
import os


from homework import check_response, check_tokens, get_api_answer, parse_status
from homework import ENDPOINT, HEADERS
from exceptions import (
    ApiConnectionFailed, HomeworksNotListError,
    KeyNotExistsError, ResponseNotDictError, HomeworkStatusError
)


time_stamp = 0
current_time_stamp = int(time.time())
hw_status_zero = ('Изменился статус проверки работы "hw05_final-master.zip". '
                  'Работа проверена: ревьюеру всё понравилось. Ура!')


class TestHomeworkBot(unittest.TestCase):
    """Testing bot from homemwork."""

    def setUp(self) -> None:
        """Setting up different time period responses."""
        self.response_zero = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': time_stamp}
        ).json()
        self.response_current = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': current_time_stamp}
        ).json()

    def test_check_tokens(self) -> None:
        """Checking check_tokens result."""
        call = check_tokens()
        check = ('PRACTICUM_TOKEN' and 'TELEGRAM_TOKEN'
                 and 'TELEGRAM_CHAT_ID' in os.environ)
        result = bool
        self.assertEqual(type(call), result)
        self.assertEqual(call, check)

    def test_get_api_answer(self) -> None:
        """Checking get_api_answer result."""
        call = get_api_answer(time_stamp)
        result = self.response_zero
        key = 'homeworks'
        self.assertEqual(call[key], result[key])
        self.assertEqual(type(call), dict)

        call = get_api_answer(current_time_stamp)
        result = self.response_current
        self.assertEqual(call[key], result[key])

        """Checking get_api_answer Exceptions."""
        self.assertRaises(ApiConnectionFailed, get_api_answer, 'asasasa')

    def test_check_response(self) -> None:
        """Checking check_response reuslt."""
        call = check_response(self.response_zero)
        result = self.response_zero['homeworks'][0]
        self.assertEqual(call, result)

        """Checking check_response Exceptions."""
        error_cases = {
            ResponseNotDictError: 'foo',
            KeyNotExistsError: {},
            HomeworksNotListError: {'homeworks': 123},
        }
        for error, case in error_cases.items():
            with self.subTest(field=case):
                self.assertRaises(error, check_response, case)

    def test_check_parse_status(self) -> None:
        """Checking parse_status result."""
        call = parse_status(check_response(self.response_zero))
        result = hw_status_zero
        self.assertEqual(call, result)

        """Checking parse_status Exceptions."""
        error_cases = {
            KeyNotExistsError: {'foor': 'bar'},
            HomeworkStatusError: {'homework_name': 'name'},
        }
        for error, case in error_cases.items():
            with self.subTest(field=case):
                self.assertRaises(error, parse_status, case)


if __name__ == '__main__':
    unittest.main()
