from flask import Blueprint

from app.common.envelope import ok
from app.common.openapi import document
from app.common.validation import load_body

from . import service
from .schema import LoginOutSchema, LoginSchema, RegisterOutSchema, RegisterSchema

bp = Blueprint("auth", __name__)


@bp.post("/api/auth/register")
@document(
    summary="Register a new user",
    request=RegisterSchema,
    success=RegisterOutSchema,
    status=201,
    public=True,
    conflict=True,
)
def register():
    data = load_body(RegisterSchema())
    user = service.register_user(data)
    return ok(RegisterOutSchema().dump(user), 201)


@bp.post("/api/auth/login")
@document(
    summary="Log in and obtain an access token",
    request=LoginSchema,
    success=LoginOutSchema,
    status=200,
    public=True,
)
def login():
    data = load_body(LoginSchema())
    user, token, expires_in = service.login(data)
    payload = {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user": user,
    }
    return ok(LoginOutSchema().dump(payload))
