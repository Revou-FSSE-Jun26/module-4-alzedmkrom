"""JWT decorators and error callbacks (BE-AUTH-01..04)."""
import uuid
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.errors import Unauthenticated, error_body
from app.extensions import db
from app.models import User


def _user_from_identity(identity):
    try:
        user_id = uuid.UUID(str(identity))
    except ValueError:
        raise Unauthenticated("Invalid or expired token.") from None
    user = db.session.get(User, user_id)
    if user is None:
        raise Unauthenticated("Invalid or expired token.")
    return user


def current_user():
    return g.get("current_user")


def auth_required(fn):
    """Protected route: a valid token is mandatory (401 otherwise)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        g.current_user = _user_from_identity(get_jwt_identity())
        return fn(*args, **kwargs)

    return wrapper


def auth_optional(fn):
    """Public route: no token means Anonymous. A present but invalid token is still 401."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        g.current_user = None if identity is None else _user_from_identity(identity)
        return fn(*args, **kwargs)

    return wrapper


def register_jwt_callbacks(jwt):
    """flask_jwt_extended calls these and returns their result as the response."""
    message = "Invalid or expired token."

    def unauthorized(_reason):
        return jsonify(error_body("UNAUTHENTICATED", "Authentication required.")), 401

    @jwt.invalid_token_loader
    def invalid(_reason):
        return jsonify(error_body("UNAUTHENTICATED", message)), 401

    @jwt.expired_token_loader
    def expired(_header, _payload):
        return jsonify(error_body("UNAUTHENTICATED", message)), 401

    jwt.unauthorized_loader(unauthorized)
