from typing import Any

from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy import func, select

from app.common.auth import hash_password, verify_password
from app.common.db import commit_or_conflict
from app.common.errors import Conflict, Unauthorized
from app.extensions import db
from app.models.user import User


def register_user(data: dict[str, Any]) -> User:
    email = data["email"]
    exists = db.session.execute(
        select(User.id).where(func.lower(User.email) == email.lower())
    ).first()
    if exists is not None:
        raise Conflict("Email already registered")
    user = User(
        name=data["name"],
        email=email,
        password_hash=hash_password(data["password"]),
    )
    db.session.add(user)
    # A concurrent loser hits uq_users_email_lower and becomes 409 here.
    commit_or_conflict()
    return user


def login(data: dict[str, Any]) -> tuple[User, str, int]:
    email = data["email"].strip().lower()
    user = db.session.execute(
        select(User).where(func.lower(User.email) == email)
    ).scalar_one_or_none()
    if not verify_password(user.password_hash if user else None, data["password"]):
        raise Unauthorized("Invalid email or password")
    assert user is not None
    token = create_access_token(identity=str(user.id))
    expires_in = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
    return user, token, expires_in
