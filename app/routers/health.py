from fastapi import APIRouter

# Create the router instance that main.py imports
router = APIRouter()

@router.get("/health")  # Fixed the typo from "heath" to "health"
async def health_check():
    return {"status": "ok"}