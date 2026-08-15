import jwt
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from app.core.config import settings

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"

async def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
        
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]}
        )
        
        uid_str = payload.get("sub")
        if uid_str is None:
            raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
            
        return int(uid_str)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
    except (jwt.PyJWTError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})