from typing import Any

from sqlalchemy import func, select

from app.common.db import commit_or_conflict
from app.common.errors import Conflict
from app.extensions import db
from app.models.user import User


def get_profile(user: User) -> User:
    return user


def update_profile(user: User, data: dict[str, Any]) -> User:
    if "email" in data:
        email = data["email"].strip().lower()
        other = db.session.execute(
            select(User.id).where(
                func.lower(User.email) == email, User.id != user.id
            )
        ).first()
        if other is not None:
            raise Conflict("Email already registered")
        user.email = email
    if "name" in data:
        user.name = data["name"]
    # updated_at is set by the database trigger. A concurrent loser hits
    # uq_users_email_lower and becomes 409 here.
    commit_or_conflict()
    db.session.refresh(user)
    return user
