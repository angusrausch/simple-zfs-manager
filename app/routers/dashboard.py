import os
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.core.security import get_current_user
router = APIRouter()

# Dynamically finds the absolute path to simple-zfs-manager/app/templates
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(base_dir, "templates")

templates = Jinja2Templates(directory=templates_dir)

@router.get("/")
async def read_home(request: Request, uid: int = Depends(get_current_user)):
    return templates.TemplateResponse(
        request, 
        "dashboard.html",
        {}
    )