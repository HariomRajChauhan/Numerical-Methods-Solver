"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness/readiness probe used by docker-compose and the frontend."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
