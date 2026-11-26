"""Registration and login (BE-AUTH-01, BE-AUTH-02)."""
from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from app.blueprints.auth.schema import LoginSchema, RegisterSchema
from app.errors import Conflict, Unauthenticated
from app.extensions import db
from app.models import User
from app.schemas import parse
from app.transactions import transactional


@transactional
def register(payload):
    data = parse(RegisterSchema, payload)
    taken = db.session.scalar(select(User.id).where(func.lower(User.email) == data["email"]))
    if taken is not None:
        raise Conflict("Email is already registered.", code="EMAIL_TAKEN")
    user = User(
        name=data["name"],
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
    )
    db.session.add(user)
    return user


def login(payload):
    data = parse(LoginSchema, payload)
    user = db.session.scalar(select(User).where(func.lower(User.email) == data["email"]))
    if user is None or not check_password_hash(user.password_hash, data["password"]):
        raise Unauthenticated("Invalid email or password.")
    token = create_access_token(identity=str(user.id))
    lifetime = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": int(lifetime.total_seconds()),
    }
