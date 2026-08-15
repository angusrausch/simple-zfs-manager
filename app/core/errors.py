class InvalidCredentialsError(Exception):
    def __init__(self, detail: str = "Incorrect username or password"):
        super().__init__(detail)
