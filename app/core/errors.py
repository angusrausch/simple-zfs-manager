import logging

audit_logger = logging.getLogger("app.audit")

class InvalidCredentialsError(Exception):
    def __init__(self, detail: str = "Incorrect username or password"):
        super().__init__(detail)


class InvalidUsernameFormatError(ValueError):
    def __init__(self, detail: str = "Invalid username format"):
        super().__init__(detail)


class FileIntegrityError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

    @classmethod
    def log_and_raise(cls, detail: str):
        """Logs the specific error details and raises the subclass."""
        audit_logger.error(f"[FILE] {detail}")
        return cls(detail)

class MissingInputFileError(FileIntegrityError): pass
class LockFileMismatchError(FileIntegrityError): pass
class LockPathBlockedError(FileIntegrityError): pass
class PathBlockedError(FileIntegrityError): pass
class CannotWriteError(FileIntegrityError): pass