from sqlalchemy import func, select

from app.blueprints.users.schema import UserUpdateSchema
from app.errors import Conflict
from app.extensions import db
from app.models import User
from app.schemas import parse
from app.transactions import transactional


@transactional
def update_me(user, payload):
    data = parse(UserUpdateSchema, payload)
    if "email" in data:
        taken = db.session.scalar(
            select(User.id).where(func.lower(User.email) == data["email"], User.id != user.id)
        )
        if taken is not None:
            raise Conflict("Email is already registered.", code="EMAIL_TAKEN")
        user.email = data["email"]
    if "name" in data:
        user.name = data["name"]
    return user
