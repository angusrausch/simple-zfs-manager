import re
from pathlib import Path
from fastapi import HTTPException, status

from app.core.errors import InvalidUsernameFormatError

USERNAME_REGEX = re.compile(r'^[a-z_][a-z0-9_-]{0,31}$')

def sanitise_username(username: str) -> str:
    username = username.strip().lower()
    
    if not USERNAME_REGEX.match(username):
        raise InvalidUsernameFormatError()
    return username


def sanitise_path(path: Path | str) -> Path | str:
    if not isinstance(path, (str, Path)):
        raise TypeError(f"Expected str or Path, got {type(path).__name__}")

    expanded = Path(path).expanduser()
    cleaned_str = re.sub(r'[\x00-\x1f]', '', str(expanded))
    resolved_path = Path(cleaned_str).resolve()

    return str(resolved_path) if isinstance(path, str) else resolved_path