class InvalidCredentialsError(Exception):
    def __init__(self, detail: str = "Incorrect username or password"):
        super().__init__(detail)


class InvalidUsernameFormatError(ValueError):
    def __init__(self, detail: str = "Invalid username format"):
        super().__init__(detail)