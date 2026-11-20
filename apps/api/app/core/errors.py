"""Error contract (system PRD 4.2, API PRD section 1).

Every error body is `{"code", "message"}`; 422s add `fields`. Clients switch on `code`.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Raise from services or dependencies to return `{"code", "message"}` with a status."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


class ErrorResponse(BaseModel):
    code: str
    message: str


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(ErrorResponse):
    fields: list[FieldError]


# Merged into every router so the OpenAPI schema documents the real error shapes.
COMMON_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ValidationErrorResponse, "description": "VALIDATION_ERROR"},
}

_HTTP_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def error_responses(*errors: tuple[int, str]) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries for the listed (status, code) pairs."""
    grouped: dict[int, list[str]] = {}
    for status, code in errors:
        grouped.setdefault(status, []).append(code)
    return {
        status: {"model": ErrorResponse, "description": " | ".join(codes)}
        for status, codes in grouped.items()
    }


def _body(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _field_name(loc: tuple[int | str, ...]) -> str:
    # loc starts with "body" / "query" / "path" / "header"; drop it unless it is all there is.
    parts = loc[1:] if len(loc) > 1 else loc
    return ".".join(str(part) for part in parts)


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code, content=_body(exc.code, exc.message), headers=exc.headers
    )


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(code, str(exc.detail)),
        headers=exc.headers,
    )


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields = [
        {"field": _field_name(tuple(error["loc"])), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={**_body("VALIDATION_ERROR", "Request validation failed."), "fields": fields},
    )


async def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500, content=_body("INTERNAL_ERROR", "An unexpected error occurred.")
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
