import os
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

from app.core.security import get_current_user
from app.core.templates import templates

router = APIRouter()

@router.get("/")
async def read_home(request: Request, uid: int = Depends(get_current_user)):
    return templates.TemplateResponse(
        request, 
        "dashboard.html",
        {}
    )