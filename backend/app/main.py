import httpx
from fastapi import APIRouter, FastAPI

from app.config import get_settings
from app.db import D1Client, D1Error

app = FastAPI(title="Wind Forecast API", version="0.1.0")
v1 = APIRouter(prefix="/api/v1")


@v1.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    if not settings.d1_configured:
        return {"status": "ok", "db": "not configured"}
    try:
        await D1Client(settings).query("SELECT 1")
        db = "ok"
    except (D1Error, httpx.HTTPError):
        db = "error"
    return {"status": "ok", "db": db}


app.include_router(v1)
