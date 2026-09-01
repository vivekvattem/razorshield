from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import error_payload, request_id_for

router = APIRouter()


@router.get("/", tags=["operational"])
def root(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs_path": "/docs",
    }


@router.get("/health", tags=["operational"])
def health() -> dict[str, str]:
    """Liveness is process-only and intentionally does not contact the database."""
    return {"status": "ok"}


@router.get("/ready", tags=["operational"])
def ready(request: Request) -> dict[str, str] | JSONResponse:
    try:
        request.app.state.database.ping()
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content=error_payload(
                "database_unavailable",
                "Database connectivity check failed",
                request_id_for(request),
            ),
        )
    return {"status": "ready", "database": "available", "model": "not_configured"}
