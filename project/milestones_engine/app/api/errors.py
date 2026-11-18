"""The uniform error envelope.

Every failure the API reports comes out of here, with the same shape:
``{"error": {"code", "message", "details"}}``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError
from app.logging_config import get_logger
from app.schemas.common import ErrorBody, ErrorResponse

logger = get_logger(__name__)


def error_response(
    code: str, message: str, status_code: int, details: dict | None = None
) -> JSONResponse:
    """Build the JSON body of an error."""
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {})
    )
    return JSONResponse(
        status_code=status_code, content=payload.model_dump(exclude_none=True)
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the handlers that produce the error envelope."""

    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {"errors": _summarise(exc)}
        return error_response(
            "VALIDATION_ERROR",
            "The request payload is not valid",
            422,
            details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return error_response(code, str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error: %s", type(exc).__name__)
        return error_response(
            "DATABASE_ERROR" if _is_database_error(exc) else "INTERNAL_ERROR",
            "Something went wrong while handling the request",
            500,
        )


def _summarise(exc: RequestValidationError) -> list[dict]:
    summary: list[dict] = []
    for error in exc.errors()[:10]:
        summary.append(
            {
                "field": ".".join(str(part) for part in error.get("loc", [])),
                "message": error.get("msg", "invalid value"),
            }
        )
    return summary


def _is_database_error(exc: Exception) -> bool:
    name = type(exc).__name__
    return name.startswith("SQLAlchemy") or "OperationalError" in name or (
        "IntegrityError" in name
    )
