from flask import Blueprint, request, jsonify

from app.auth_utils import auth_optional, auth_required, current_user
from app.blueprints.boards import service
from app.blueprints.boards.schema import BoardSchema, MemberSchema
from app.extensions import db
from app.permissions import resolve_board_role
from app.models import Board

bp = Blueprint("boards", __name__)


def _board_out(user, board):
    return {**BoardSchema().dump(board), "my_role": resolve_board_role(user, board)}


@bp.get("/api/boards")
@auth_optional
def list_boards():
    return jsonify(service.list_boards(current_user(), request.args.to_dict())), 200


@bp.post("/api/boards")
@auth_required
def create_board():
    board = service.create_board(current_user(), request.get_json(silent=True))
    return jsonify(_board_out(current_user(), board)), 201


@bp.get("/api/boards/<uuid:board_id>")
@auth_optional
def get_board(board_id):
    return jsonify(service.get_board(current_user(), board_id)), 200


@bp.patch("/api/boards/<uuid:board_id>")
@auth_required
def update_board(board_id):
    board = service.update_board(current_user(), board_id, request.get_json(silent=True))
    return jsonify(_board_out(current_user(), board)), 200


@bp.delete("/api/boards/<uuid:board_id>")
@auth_required
def delete_board(board_id):
    service.delete_board(current_user(), board_id)
    return "", 204


@bp.get("/api/boards/<uuid:board_id>/members")
@auth_required
def list_members(board_id):
    return jsonify({"items": service.list_members(current_user(), board_id)}), 200


@bp.post("/api/boards/<uuid:board_id>/members")
@auth_required
def add_member(board_id):
    member, person = service.add_member(current_user(), board_id, request.get_json(silent=True))
    return jsonify(_member_out(member, person)), 201


@bp.patch("/api/boards/<uuid:board_id>/members/<uuid:user_id>")
@auth_required
def update_member(board_id, user_id):
    member, person = service.update_member(
        current_user(), board_id, user_id, request.get_json(silent=True)
    )
    return jsonify(_member_out(member, person)), 200


@bp.delete("/api/boards/<uuid:board_id>/members/<uuid:user_id>")
@auth_required
def remove_member(board_id, user_id):
    service.remove_member(current_user(), board_id, user_id)
    return "", 204


def _member_out(member, person):
    """Admins see emails. Admin status is checked on the caller's own row."""
    board = db.session.get(Board, member.board_id)
    viewer_is_admin = resolve_board_role(current_user(), board) == "admin"
    return MemberSchema().dump(
        {
            "user_id": person.id,
            "name": person.name,
            "email": person.email if viewer_is_admin else None,
            "role": member.role,
            "created_at": member.created_at,
        }
    )
