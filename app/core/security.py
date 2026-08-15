import jwt
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from app.core.config import settings

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"

async def _decode_token(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    
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
        if uid_str is None:
            return None
            
        return int(uid_str)
    except (jwt.jwt.ExpiredSignatureError, jwt.PyJWTError, ValueError):
        return None

async def get_current_user(request: Request):
    uid = await _decode_token(request)

    if uid is None:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
    
    return uid

async def user_logged_in(request: Request):
    return await _decode_token(request) is not None
