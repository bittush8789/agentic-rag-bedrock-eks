from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
async def liveness():
    """Returns basic service health status for Kubernetes liveness probe."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database="unknown",
        environment=settings.ENVIRONMENT
    )


@router.get("/ready", response_model=HealthResponse, summary="Readiness Probe")
async def readiness(response: Response, db: AsyncSession = Depends(get_db)):
    """Verifies database connectivity for Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1;"))
        db_status = "connected"
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        db_status = f"unhealthy: {str(e)}"
        return HealthResponse(
            status="unready",
            version="1.0.0",
            database=db_status,
            environment=settings.ENVIRONMENT
        )

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=db_status,
        environment=settings.ENVIRONMENT
    )
