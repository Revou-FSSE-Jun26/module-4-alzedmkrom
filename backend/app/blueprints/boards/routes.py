from flask import Blueprint

from app.common.access import (
    get_board_for_user,
    require_admin,
    require_admin_or_self,
)
from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.errors import NotFound
from app.common.openapi import document
from app.common.schemas import IdOutSchema
from app.common.validation import load_body, parse_uuid

from . import service
from .schema import (
    BoardCreateSchema,
    BoardDetailOutSchema,
    BoardOutSchema,
    BoardUpdateSchema,
    MemberAddSchema,
    MemberOutSchema,
    MemberRemovedOutSchema,
    MemberRoleSchema,
)

bp = Blueprint("boards", __name__)


@bp.post("/api/boards")
@document(
    summary="Create a board",
    request=BoardCreateSchema,
    success=BoardOutSchema,
    status=201,
    conflict=True,
)
@protected
def create_board():
    user = current_user()
    data = load_body(BoardCreateSchema())
    board = service.create_board(user, data)
    return ok(BoardOutSchema().dump(board), 201)


@bp.get("/api/boards")
@document(
    summary="List the boards the current user belongs to",
    success=BoardOutSchema,
    many=True,
    status=200,
)
@protected
def list_boards():
    boards = service.list_boards(current_user())
    return ok(BoardOutSchema(many=True).dump(boards))


@bp.get("/api/boards/<board_id>")
@document(
    summary="Get a board with its columns and cards",
    success=BoardDetailOutSchema,
    status=200,
)
@protected
def get_board(board_id):
    access = get_board_for_user(current_user().id, board_id)
    detail = service.get_board_detail(access)
    return ok(BoardDetailOutSchema().dump(detail))


@bp.patch("/api/boards/<board_id>")
@document(
    summary="Rename a board (admin only)",
    request=BoardUpdateSchema,
    success=BoardOutSchema,
    status=200,
    conflict=True,
)
@protected
def rename_board(board_id):
    access = get_board_for_user(current_user().id, board_id)
    require_admin(access)
    data = load_body(BoardUpdateSchema())
    board = service.rename_board(access, data)
    return ok(BoardOutSchema().dump(board))


@bp.delete("/api/boards/<board_id>")
@document(
    summary="Delete a board (admin only)",
    success=IdOutSchema,
    status=200,
    conflict=True,
)
@protected
def delete_board(board_id):
    access = get_board_for_user(current_user().id, board_id)
    require_admin(access)
    result = service.delete_board(access)
    return ok(IdOutSchema().dump(result))


@bp.get("/api/boards/<board_id>/members")
@document(
    summary="List the members of a board",
    success=MemberOutSchema,
    many=True,
    status=200,
)
@protected
def list_members(board_id):
    access = get_board_for_user(current_user().id, board_id)
    return ok(MemberOutSchema(many=True).dump(service.list_members(access)))


@bp.post("/api/boards/<board_id>/members")
@document(
    summary="Add a member to a board (admin only)",
    request=MemberAddSchema,
    success=MemberOutSchema,
    status=201,
    conflict=True,
)
@protected
def add_member(board_id):
    user = current_user()
    access = get_board_for_user(user.id, board_id)
    require_admin(access)
    data = load_body(MemberAddSchema())
    member = service.add_member(access, user, data)
    return ok(MemberOutSchema().dump(member), 201)


@bp.patch("/api/boards/<board_id>/members/<user_id>")
@document(
    summary="Change a member's role (admin only)",
    request=MemberRoleSchema,
    success=MemberOutSchema,
    status=200,
    conflict=True,
)
@protected
def change_member_role(board_id, user_id):
    user = current_user()
    access = get_board_for_user(user.id, board_id)
    require_admin(access)
    data = load_body(MemberRoleSchema())
    member = service.change_member_role(access, user, parse_uuid(user_id), data)
    return ok(MemberOutSchema().dump(member))


@bp.delete("/api/boards/<board_id>/members/<user_id>")
@document(
    summary="Remove a member from a board (admin or the member themselves)",
    success=MemberRemovedOutSchema,
    status=200,
    conflict=True,
)
@protected
def remove_member(board_id, user_id):
    user = current_user()
    access = get_board_for_user(user.id, board_id)
    try:
        target = parse_uuid(user_id)
    except NotFound:
        # D20: a non-admin must get 403 before any target lookup result.
        require_admin(access)
        raise
    require_admin_or_self(access, user.id, target)
    result = service.remove_member(access, user, target)
    return ok(MemberRemovedOutSchema().dump(result))