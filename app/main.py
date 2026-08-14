import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from app.routers import health

load_dotenv()

app = FastAPI(title="Simple ZFS Manager")

app.include_router(health.router)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=True,
    )