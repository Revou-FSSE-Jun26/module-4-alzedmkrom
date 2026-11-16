from flask import Blueprint

from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.openapi import document
from app.common.validation import load_body

from . import service
from .schema import ProfileOutSchema, ProfileUpdateSchema

bp = Blueprint("users", __name__)


@bp.get("/api/users/me")
@document(
    summary="Get the current user's profile",
    success=ProfileOutSchema,
    status=200,
)
@protected
def get_me():
    user = service.get_profile(current_user())
    return ok(ProfileOutSchema().dump(user))


@bp.patch("/api/users/me")
@document(
    summary="Update the current user's profile",
    request=ProfileUpdateSchema,
    success=ProfileOutSchema,
    status=200,
    conflict=True,
)
@protected
def update_me():
    data = load_body(ProfileUpdateSchema())
    user = service.update_profile(current_user(), data)
    return ok(ProfileOutSchema().dump(user))
