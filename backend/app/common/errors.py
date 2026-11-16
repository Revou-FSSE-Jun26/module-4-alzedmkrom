from typing import Any, Mapping

from flask import Flask
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.common.envelope import error_response, format_field_errors
from app.extensions import db


class ApiError(Exception):
    status: int = 500
    message: str = "Internal server error"

    def __init__(self, message: str | None = None):
        if message is not None:
            self.message = message
        super().__init__(self.message)


class Unauthorized(ApiError):
    status = 401
    message = "Authentication required"


class Forbidden(ApiError):
    status = 403
    message = "Forbidden"


class NotFound(ApiError):
    status = 404
    message = "Resource not found"


class Conflict(ApiError):
    status = 409
    message = "Conflict"


class ValidationFailed(ApiError):
    status = 400
    message = "Invalid request"

    def __init__(self, errors: Mapping[str, Any] | str):
        text = errors if isinstance(errors, str) else format_field_errors(errors)
        super().__init__(text)


_HTTP_TEXT = {
    404: "Resource not found",
    405: "Method not allowed",
    413: "Request body too large",
}


def _rollback() -> None:
    try:
        db.session.rollback()
    except Exception:  # pragma: no cover - rollback must never mask the error
        pass


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(e: ApiError):
        return error_response(e.status, e.message)

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e: IntegrityError):
        _rollback()
        if getattr(e.orig, "pgcode", None) == "23505":
            return error_response(409, "Resource already exists")
        return error_response(400, "Request violates a data constraint")

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        code = e.code or 500
        return error_response(code, _HTTP_TEXT.get(code, e.name))

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        _rollback()
        app.logger.exception("Unhandled exception")
        return error_response(500, "Internal server error")
