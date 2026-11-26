from flask import Blueprint, jsonify, request

from app.blueprints.auth import service
from app.blueprints.auth.schema import LoginSchema, RegisterSchema
from app.blueprints.users.schema import UserSchema
from app.openapi import document

bp = Blueprint("auth", __name__)


@bp.post("/api/auth/register")
@document(
    summary="Register a new account",
    tags=["auth"],
    request=RegisterSchema,
    success=UserSchema,
    public=True,
    status=201,
    conflict=True,
)
def register():
    user = service.register(request.get_json(silent=True))
    return jsonify(UserSchema().dump(user)), 201


@bp.post("/api/auth/login")
@document(
    summary="Log in and receive a JWT",
    tags=["auth"],
    request=LoginSchema,
    success=None,
    public=True,
    status=200,
)
def login():
    return jsonify(service.login(request.get_json(silent=True))), 200
