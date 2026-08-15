import os
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Dynamically finds the absolute path to simple-zfs-manager/app/templates
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(base_dir, "templates")

templates = Jinja2Templates(directory=templates_dir)

@router.get("/")
async def read_home(request: Request):
    return templates.TemplateResponse(
        request, 
        "dashboard.html",
        {}
    )