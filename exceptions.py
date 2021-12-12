class ApiNotFoundError(Exception):
    """Exception for 404 API answer code."""

    def __init__(self, *args) -> None:
        super().__init__(
            'Endpoint not found, code: 404'
        )


class ApiConnectionFailed(Exception):
    """Exception for any API answer code except 404 and 200."""

    def __init__(self, status_code) -> None:
        self.status_code = status_code
        super().__init__(
            f'Connection problem code: {self.status_code}'
        )


class ResponseNotDictError(TypeError):
    """Exception if response type is not dict."""

    def __init__(self, response) -> None:
        self.response_type = type(response)
        super().__init__(
            f'Response type is not dict but {self.response_type}'
        )


class KeyNotExistsError(KeyError):
    """Exception if key does not exist."""

    def __init__(self, key) -> None:
        self.key = key
        super().__init__(
            f'Key "{key}" does not exist in response'
        )


class HomeworksNotListError(Exception):
    """Exception if variable type is not list."""

    def __init__(self, homework) -> None:
        self.hw_type = type(homework)
        super().__init__(
            f'Homeworks type is not list but {self.hw_type}'
        )


class HomeworkStatusError(Exception):
    """Exception for checking homework_status."""

    def __init__(self, status) -> None:
        self.status = status
        if self.status is None:
            self.status = 'Missing key "status"'
        super().__init__(
            f'Undocumented homework status found in the answer: {self.status}'
        )


class CheckTokensError(Exception):
    """Exception if tokens not in env."""

    def __init__(self, var) -> None:
        self.var = var
        super().__init__(
            f'Failed beacause {var} is not set.'
        )
