"""Error classes and the single error envelope (BE-ERR-01, BE-ERR-02, BE-ERR-04)."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from app.extensions import db

log = logging.getLogger(__name__)


class ApiError(Exception):
    """Base for every error the API returns on purpose."""

    status = 500
    code = "INTERNAL_ERROR"
    message = "Something went wrong."

    def __init__(self, message=None, *, code=None, details=None):
        self.message = message or self.message
        if code:
            self.code = code
        self.details = details
        super().__init__(self.message)


class BadRequest(ApiError):
    status = 400
    code = "BAD_REQUEST"
    message = "Malformed request."


class Unauthenticated(ApiError):
    status = 401
    code = "UNAUTHENTICATED"
    message = "Authentication required."


class Forbidden(ApiError):
    status = 403
    code = "FORBIDDEN"
    message = "You do not have permission to do this."


class NotFound(ApiError):
    status = 404
    code = "NOT_FOUND"
    message = "Resource not found."


class Conflict(ApiError):
    status = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state."


class ValidationFailed(ApiError):
    status = 422
    code = "VALIDATION_ERROR"
    message = "Invalid request data."


def error_body(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details}}


_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(error_body(err.code, err.message, err.details)), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        code = _HTTP_CODES.get(err.code, "BAD_REQUEST")
        message = err.description if err.code != 404 else NotFound.message
        return jsonify(error_body(code, message)), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        log.exception("Unhandled error")
        return jsonify(error_body("INTERNAL_ERROR", "Something went wrong.")), 500
