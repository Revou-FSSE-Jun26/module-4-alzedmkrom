from flask import Blueprint, jsonify, request

from app.auth_utils import auth_required, current_user
from app.blueprints.columns import service
from app.blueprints.columns.schema import (
    ColumnCreateSchema,
    ColumnReorderSchema,
    ColumnSchema,
    ColumnUpdateSchema,
)
from app.openapi import document

bp = Blueprint("columns", __name__)


@bp.post("/api/boards/<uuid:board_id>/columns")
@auth_required
@document(
    summary="Add a column to a board",
    tags=["columns"],
    request=ColumnCreateSchema,
    success=ColumnSchema,
    status=201,
)
def create_column(board_id):
    column = service.create_column(current_user(), board_id, request.get_json(silent=True))
    return jsonify(ColumnSchema().dump(column)), 201


@bp.patch("/api/boards/<uuid:board_id>/columns/reorder")
@auth_required
@document(
    summary="Move a column to a new position",
    tags=["columns"],
    request=ColumnReorderSchema,
    success=ColumnSchema,
)
def reorder_column(board_id):
    column, placement = service.reorder_column(
        current_user(), board_id, request.get_json(silent=True)
    )
    body = {
        **ColumnSchema().dump(column),
        "rebalanced": placement.rebalanced,
        "siblings": placement.siblings(),
    }
    return jsonify(body), 200


@bp.patch("/api/columns/<uuid:column_id>")
@auth_required
@document(
    summary="Rename a column or mark it as done",
    tags=["columns"],
    request=ColumnUpdateSchema,
    success=ColumnSchema,
    conflict=True,
)
def update_column(column_id):
    column = service.update_column(current_user(), column_id, request.get_json(silent=True))
    return jsonify(ColumnSchema().dump(column)), 200


@bp.delete("/api/columns/<uuid:column_id>")
@auth_required
@document(
    summary="Delete a column and its cards",
    tags=["columns"],
    success=None,
    status=204,
    conflict=True,
)
def delete_column(column_id):
    service.delete_column(current_user(), column_id)
    return "", 204
