from fastapi import APIRouter, FastAPI

from app.api import router as data_router
from app.db import DatabaseError, get_default_database

app = FastAPI(title="Wind Forecast API", version="0.1.0")
v1 = APIRouter(prefix="/api/v1")


@v1.get("/health")
async def health() -> dict[str, str]:
    try:
        await get_default_database().query("SELECT 1")
        db = "ok"
    except DatabaseError:
        db = "error"
    return {"status": "ok", "db": db}


v1.include_router(data_router)
app.include_router(v1)
