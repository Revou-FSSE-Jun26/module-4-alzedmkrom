import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

from flask_jwt_extended import JWTManager, jwt_required
from flask_jwt_extended import current_user as _jwt_current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.common.envelope import error_response
from app.extensions import db
from app.models.user import User

F = TypeVar("F", bound=Callable[..., Any])

# Checked when no user matches, so an unknown email costs the same as a wrong password.
DUMMY_HASH = generate_password_hash("revotask-dummy-password")


def hash_password(raw: str) -> str:
    return generate_password_hash(raw)


def verify_password(stored_hash: str | None, raw: str) -> bool:
    if stored_hash is None:
        check_password_hash(DUMMY_HASH, raw)
        return False
    return check_password_hash(stored_hash, raw)


def protected(fn: F) -> F:
    """Require a valid access token whose subject is an existing User."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.__protected__ = True  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]


def current_user() -> User:
    return _jwt_current_user


def register_jwt_callbacks(jwt: JWTManager) -> None:
    @jwt.user_lookup_loader
    def load_user(_header, payload):
        try:
            user_id = uuid.UUID(str(payload.get("sub")))
        except ValueError:
            return None
        return db.session.get(User, user_id)

    def unauthorized(*_args):
        return error_response(401, "Authentication required")

    jwt.unauthorized_loader(unauthorized)
    jwt.invalid_token_loader(unauthorized)
    jwt.expired_token_loader(unauthorized)
    jwt.user_lookup_error_loader(unauthorized)
    jwt.revoked_token_loader(unauthorized)
