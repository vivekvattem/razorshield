from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def request_id_for(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def error_payload(code: str, message: str, request_id: str, details: Any = None) -> dict[str, Any]:
<<<<<<< HEAD
    payload: dict[str, Any] = {"error": {"code": code, "message": message, "request_id": request_id}}
=======
    payload: dict[str, Any] = {
        "error": {"code": code, "message": message, "request_id": request_id}
    }
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
    if details is not None:
        payload["error"]["details"] = details
    return payload


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, str(exc.detail), request_id_for(request)),
    )


<<<<<<< HEAD
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
=======
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "validation_error",
            "Request validation failed",
            request_id_for(request),
            details=exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_payload("internal_error", "An unexpected error occurred", request_id_for(request)),
    )
