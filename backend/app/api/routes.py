from __future__ import annotations

<<<<<<< HEAD
from fastapi import APIRouter, Query, Request
=======
from fastapi import APIRouter, Request
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
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
<<<<<<< HEAD
def health(verbose: bool = Query(default=False)) -> dict[str, str]:
    """Liveness is process-only and intentionally does not contact the database."""
    response = {"status": "ok"}
    if verbose:
        response["service"] = "razorshield"
    return response


@router.get("/ready", tags=["operational"], response_model=None)
=======
def health() -> dict[str, str]:
    """Liveness is process-only and intentionally does not contact the database."""
    return {"status": "ok"}


@router.get("/ready", tags=["operational"])
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
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
