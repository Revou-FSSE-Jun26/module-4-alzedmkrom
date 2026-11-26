from flask import Blueprint, jsonify, request

from app.auth_utils import auth_required, current_user
from app.blueprints.users import service
from app.blueprints.users.schema import UserSchema

bp = Blueprint("users", __name__)


@bp.get("/api/users/me")
@auth_required
def get_me():
    return jsonify(UserSchema().dump(current_user())), 200


@bp.patch("/api/users/me")
@auth_required
def update_me():
    user = service.update_me(current_user(), request.get_json(silent=True))
    return jsonify(UserSchema().dump(user)), 200
