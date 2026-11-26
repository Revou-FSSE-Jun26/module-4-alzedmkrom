from flask import Blueprint, jsonify, request

from app.auth_utils import auth_optional, auth_required, current_user
from app.blueprints.boards import service
from app.blueprints.boards.schema import (
    BoardCreateSchema,
    BoardListQuerySchema,
    BoardSchema,
    BoardUpdateSchema,
    MemberAddSchema,
    MemberSchema,
    MemberUpdateSchema,
)
from app.openapi import document
from app.permissions import resolve_board_role

bp = Blueprint("boards", __name__)


def _board_out(user, board):
    return {**BoardSchema().dump(board), "my_role": resolve_board_role(user, board)}


@bp.get("/api/boards")
@auth_optional
@document(
    summary="List boards",
    tags=["boards"],
    success=BoardSchema,
    many=True,
    query=BoardListQuerySchema,
    public=True,
)
def list_boards():
    return jsonify(service.list_boards(current_user(), request.args.to_dict())), 200


@bp.post("/api/boards")
@auth_required
@document(
    summary="Create a board",
    tags=["boards"],
    request=BoardCreateSchema,
    success=BoardSchema,
    status=201,
)
def create_board():
    board = service.create_board(current_user(), request.get_json(silent=True))
    return jsonify(_board_out(current_user(), board)), 201


@bp.get("/api/boards/<uuid:board_id>")
@auth_optional
@document(
    summary="Get a board with its columns and cards",
    tags=["boards"],
    success=BoardSchema,
    public=True,
)
def get_board(board_id):
    return jsonify(service.get_board(current_user(), board_id)), 200


@bp.patch("/api/boards/<uuid:board_id>")
@auth_required
@document(
    summary="Rename or toggle visibility",
    tags=["boards"],
    request=BoardUpdateSchema,
    success=BoardSchema,
)
def update_board(board_id):
    board = service.update_board(current_user(), board_id, request.get_json(silent=True))
    return jsonify(_board_out(current_user(), board)), 200


@bp.delete("/api/boards/<uuid:board_id>")
@auth_required
@document(
    summary="Delete a board",
    tags=["boards"],
    success=None,
    status=204,
)
def delete_board(board_id):
    service.delete_board(current_user(), board_id)
    return "", 204


@bp.get("/api/boards/<uuid:board_id>/members")
@auth_required
@document(
    summary="List board members",
    tags=["boards"],
    success=MemberSchema,
    many=True,
)
def list_members(board_id):
    return jsonify({"items": service.list_members(current_user(), board_id)}), 200


@bp.post("/api/boards/<uuid:board_id>/members")
@auth_required
@document(
    summary="Add a member by email",
    tags=["boards"],
    request=MemberAddSchema,
    success=MemberSchema,
    status=201,
    conflict=True,
)
def add_member(board_id):
    member, person = service.add_member(current_user(), board_id, request.get_json(silent=True))
    return jsonify(_member_out(member, person)), 201


@bp.patch("/api/boards/<uuid:board_id>/members/<uuid:user_id>")
@auth_required
@document(
    summary="Change a member's role",
    tags=["boards"],
    request=MemberUpdateSchema,
    success=MemberSchema,
    conflict=True,
)
def update_member(board_id, user_id):
    member, person = service.update_member(
        current_user(), board_id, user_id, request.get_json(silent=True)
    )
    return jsonify(_member_out(member, person)), 200


@bp.delete("/api/boards/<uuid:board_id>/members/<uuid:user_id>")
@auth_required
@document(
    summary="Remove a member",
    tags=["boards"],
    success=None,
    status=204,
    conflict=True,
)
def remove_member(board_id, user_id):
    service.remove_member(current_user(), board_id, user_id)
    return "", 204


def _member_out(member, person):
    return service.member_row(current_user(), member, person)
