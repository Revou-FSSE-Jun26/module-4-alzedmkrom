from flask import Blueprint

from app.common.access import get_board_for_user, get_column_for_user
from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.openapi import document
from app.common.schemas import ColumnOutSchema, IdOutSchema
from app.common.validation import load_body

from . import service
from .schema import (
    ColumnCreateSchema,
    ColumnReorderOutSchema,
    ColumnReorderSchema,
    ColumnUpdateSchema,
)

bp = Blueprint("columns", __name__)


@bp.post("/api/boards/<board_id>/columns")
@document(
    summary="Create a column on a board",
    request=ColumnCreateSchema,
    success=ColumnOutSchema,
    status=201,
    conflict=True,
)
@protected
def create_column(board_id):
    user = current_user()
    access = get_board_for_user(user.id, board_id)
    data = load_body(ColumnCreateSchema())
    column = service.create_column(access, user, data)
    return ok(ColumnOutSchema().dump(column), 201)


@bp.patch("/api/columns/<column_id>")
@document(
    summary="Rename a column",
    request=ColumnUpdateSchema,
    success=ColumnOutSchema,
    status=200,
    conflict=True,
)
@protected
def rename_column(column_id):
    access = get_column_for_user(current_user().id, column_id)
    data = load_body(ColumnUpdateSchema())
    column = service.rename_column(access, data)
    return ok(ColumnOutSchema().dump(column))


@bp.delete("/api/columns/<column_id>")
@document(
    summary="Delete a column (its cards are left untouched)",
    success=IdOutSchema,
    status=200,
    conflict=True,
)
@protected
def delete_column(column_id):
    access = get_column_for_user(current_user().id, column_id)
    result = service.delete_column(access)
    return ok(IdOutSchema().dump(result))


@bp.patch("/api/boards/<board_id>/columns/reorder")
@document(
    summary="Move a column to a new order position",
    request=ColumnReorderSchema,
    success=ColumnReorderOutSchema,
    status=200,
    conflict=True,
)
@protected
def reorder_columns(board_id):
    access = get_board_for_user(current_user().id, board_id)
    data = load_body(ColumnReorderSchema())
    result = service.reorder_columns(access, data)
    return ok(ColumnReorderOutSchema().dump(result))
