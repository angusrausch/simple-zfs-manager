import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app.core.system.pam_auth import get_authenticated_uid
from app.utils.sanitise import sanitize_username
from app.core.config import settings
from app.core.security import ALGORITHM, COOKIE_NAME
from app.core.errors import InvalidCredentialsError

router = APIRouter()

# Dynamically finds the absolute path to simple-zfs-manager/app/templates
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(base_dir, "templates")

templates = Jinja2Templates(directory=templates_dir)

@router.get("/login")
async def read_login(request: Request):
    return templates.TemplateResponse(
        request, 
        "login.html"
    )

@router.post("/login")
async def create_login(
    request: Request,
    username: str = Form(...), 
    password: str = Form(...)
):

    try:
        username = sanitize_username(username)
        uid = await get_authenticated_uid(username, password)
    except ValueError as detail:
        return templates.TemplateResponse(
            request, 
            "login.html", 
            {"error": detail}
        )
    except InvalidCredentialsError as detail:
        return templates.TemplateResponse(
            request, 
            "login.html", 
            {"error": detail}
        )

    # Create token
    expiration = datetime.now(timezone.utc) + timedelta(hours=3)
    token_data = {"sub": str(uid), "exp": expiration}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=ALGORITHM)

    response = RedirectResponse(
        url="/", 
        status_code=status.HTTP_303_SEE_OTHER
    )
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="strict"
    )
    return response