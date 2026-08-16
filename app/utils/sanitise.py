import re
from fastapi import HTTPException, status

from app.core.errors import InvalidUsernameFormatError

USERNAME_REGEX = re.compile(r'^[a-z_][a-z0-9_-]{0,31}$')

def sanitise_username(username: str) -> str:
    username = username.strip().lower()
    
    if not USERNAME_REGEX.match(username):
        raise InvalidUsernameFormatError()
    return username