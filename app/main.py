# app/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

from app.core.config import settings
from app.routers import health, dashboard
from app.routers import health, dashboard, auth
from app.core.system.logger import setup_logging

app = FastAPI(title=settings.PROJECT_NAME)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(auth.router)

setup_logging()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )