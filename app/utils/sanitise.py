import re
from fastapi import HTTPException, status

USERNAME_REGEX = re.compile(r'^[a-z_][a-z0-9_-]{0,31}$')

def sanitize_username(username: str) -> str:
    username = username.strip()
    
    if not USERNAME_REGEX.match(username):
        raise ValueError("Invalid username format")
    return username