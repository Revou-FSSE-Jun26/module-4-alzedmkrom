from typing import Any

from sqlalchemy import select

from app.common.access import BoardAccess, ColumnAccess
from app.common.constants import ActivityAction
from app.common.db import commit_or_conflict, lock_board
from app.common.errors import NotFound
from app.common.events import log_activity
from app.common.ordering import next_order, plan_move
from app.extensions import db
from app.models.column import BoardColumn
from app.models.user import User

_COLUMN_FIELDS = ("id", "board_id", "title", "order", "created_at", "updated_at")


def _column_dict(column: BoardColumn) -> dict[str, Any]:
    return {name: getattr(column, name) for name in _COLUMN_FIELDS}


def _live_columns(board_id) -> list[BoardColumn]:
    return list(
        db.session.execute(
            select(BoardColumn)
            .where(BoardColumn.board_id == board_id, BoardColumn.deleted_at.is_(None))
            .order_by(BoardColumn.order.asc(), BoardColumn.id.asc())
        )
        .scalars()
        .all()
    )


def create_column(
    access: BoardAccess, user: User, data: dict[str, Any]
) -> dict[str, Any]:
    lock_board(access.board_id)
    order = next_order(column.order for column in _live_columns(access.board_id))
    column = BoardColumn(board_id=access.board_id, title=data["title"], order=order)
    db.session.add(column)
    db.session.flush()
    log_activity(access.board_id, user.id, ActivityAction.COLUMN_CREATED)
    commit_or_conflict()
    db.session.refresh(column)
    return _column_dict(column)


def rename_column(access: ColumnAccess, data: dict[str, Any]) -> dict[str, Any]:
    column = access.column
    column.title = data["title"]
    commit_or_conflict()
    db.session.refresh(column)
    return _column_dict(column)


def delete_column(access: ColumnAccess) -> dict[str, Any]:
    """Soft-delete the column only; its cards stay untouched (Req 7.4)."""
    column = access.column
    column.soft_delete()
    commit_or_conflict()
    return {"id": column.id}


def reorder_columns(access: BoardAccess, data: dict[str, Any]) -> dict[str, Any]:
    lock_board(access.board_id)
    columns = _live_columns(access.board_id)
    moved = next((c for c in columns if c.id == data["column_id"]), None)
    if moved is None:
        raise NotFound()
    plan = plan_move(
        [(c.id, c.order) for c in columns if c.id != moved.id],
        moved.id,
        data["order"],
    )
    for column in columns:
        new_order = plan.orders.get(column.id)
        if new_order is not None and new_order != column.order:
            column.order = new_order
    commit_or_conflict()
    ordered = sorted(_live_columns(access.board_id), key=lambda c: (c.order, c.id))
    return {
        "columns": [_column_dict(c) for c in ordered],
        "rebalanced": plan.rebalanced,
    }
