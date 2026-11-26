from flask import Blueprint, jsonify, request

from app.blueprints.auth import service
from app.blueprints.users.schema import UserSchema

bp = Blueprint("auth", __name__)


@bp.post("/api/auth/register")
def register():
    user = service.register(request.get_json(silent=True))
    return jsonify(UserSchema().dump(user)), 201


@bp.post("/api/auth/login")
def login():
    return jsonify(service.login(request.get_json(silent=True))), 200
