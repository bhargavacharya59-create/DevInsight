"""Health check endpoints."""
from datetime import datetime, UTC
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.base import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Application health check."""
    db_ok = True
    db_error = None
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        db_error = str(e)

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "version": "1.0.0",
        "database": "connected" if db_ok else f"error: {db_error}",
        "monitoring_mode": settings.MONITORING_MODE,
        "gemini_available": settings.gemini_available,
        "services": {
            "api": "up",
            "database": "up" if db_ok else "down",
        },
    }


