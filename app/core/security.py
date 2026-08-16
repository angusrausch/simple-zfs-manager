import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.system.pam_auth import get_authenticated_uid
from app.utils.sanitise import sanitise_username

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"


async def _decode_token(token: str) -> int:
    if not token:
        return None
        
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]}
        )
        
        uid_str = payload.get("sub")
        if uid_str is None or uid_str == "":
            return None
            
        return int(uid_str)
    except (jwt.ExpiredSignatureError, jwt.PyJWTError, ValueError):
        return None


async def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    uid = await _decode_token(token)

    if uid is None:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
    
    return uid


async def user_logged_in(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    return await _decode_token(token) is not None


def create_token(uid) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=3)
    token_data = {"sub": str(uid), "exp": expiration}
    return jwt.encode(token_data, settings.SECRET_KEY, algorithm=ALGORITHM)


async def create_login_token(username: str, password: str) -> str:
    sanitise_username(username)
    uid = await get_authenticated_uid(username, password)
    return create_token(uid)
