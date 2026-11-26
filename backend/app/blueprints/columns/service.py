"""Column create, edit, reorder and delete (BE-AZ-04, BE-ORD-02, BE-ORD-03, DB-DON-01)."""
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.blueprints.columns.schema import ColumnCreateSchema, ColumnReorderSchema, ColumnUpdateSchema
from app.errors import Conflict, NotFound
from app.extensions import db
from app.models import BoardColumn, Card
from app.ordering import end_order, plan_order
from app.blueprints.notifications.service import notify
from app.permissions import ADMIN, MEMBER, authorize, load_board, load_column
from app.schemas import parse
from app.transactions import lock_board, transactional


@transactional
def create_column(user, board_id, payload):
    board = load_board(board_id)
    authorize(user, "column:create", board)
    data = parse(ColumnCreateSchema, payload)
    lock_board(board.id)
    last = db.session.scalar(
        select(func.max(BoardColumn.order)).where(BoardColumn.board_id == board.id)
    )
    column = BoardColumn(
        board_id=board.id,
        name=data["name"],
        order=end_order(last),
        is_done=False,
        created_by=user.id,
    )
    db.session.add(column)
    return column


@transactional
def update_column(user, column_id, payload):
    column = load_column(column_id)
    board = load_board(column.board_id)
    authorize(user, "column:update", board)
    data = parse(ColumnUpdateSchema, payload)
    if "is_done" in data:
        authorize(user, "column:set_done", board)
        _set_done(column, data["is_done"])
    if "name" in data:
        column.name = data["name"]
    return column


def _set_done(column, value):
    """Keep DB-DON-01: one done column per board, and completed_at set only for cards in it."""
    if value == column.is_done:
        return
    if value:
        lock_board(column.board_id)
        other = db.session.scalar(
            select(BoardColumn.id).where(
                BoardColumn.board_id == column.board_id,
                BoardColumn.is_done.is_(True),
                BoardColumn.id != column.id,
            )
        )
        if other is not None:
            raise Conflict("This board already has a done column.")
        column.is_done = True
        # Includes soft-deleted cards so the completed_at invariant holds for every row.
        db.session.execute(
            update(Card)
            .where(Card.column_id == column.id, Card.completed_at.is_(None))
            .values(completed_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
    else:
        column.is_done = False
        db.session.execute(
            update(Card)
            .where(Card.column_id == column.id)
            .values(completed_at=None)
            .execution_options(synchronize_session=False)
        )


@transactional
def reorder_column(user, board_id, payload):
    board = load_board(board_id)
    authorize(user, "column:update", board)
    data = parse(ColumnReorderSchema, payload)
    column = db.session.get(BoardColumn, data["column_id"])
    if column is None or column.board_id != board.id:
        raise NotFound("Column not found on this board.")
    lock_board(board.id)
    columns = (
        BoardColumn.query.filter(BoardColumn.board_id == board.id)
        .order_by(BoardColumn.order, BoardColumn.id)
        .all()
    )
    placement = plan_order([(c.id, c.order) for c in columns], column.id, data["order"])
    by_id = {c.id: c for c in columns}
    for column_key, new_order in placement.orders.items():
        by_id[column_key].order = new_order
    return column, placement


@transactional
def delete_column(user, column_id):
    column = load_column(column_id)
    board = load_board(column.board_id)
    role = authorize(user, "column:delete", board, column)
    if role == MEMBER:
        foreign = (
            Card.active()
            .filter(
                Card.column_id == column.id,
                (Card.created_by.is_(None)) | (Card.created_by != user.id),
            )
            .count()
        )
        if foreign:
            raise Conflict(
                "The column contains cards created by other users.",
                code="COLUMN_HAS_FOREIGN_WORK",
                details={"cards": foreign},
            )
    if role == ADMIN and column.created_by is not None and column.created_by != user.id:
        notify(
            [column.created_by],
            type="column_deleted",
            message=f'Your column "{column.name}" was deleted by an administrator.',
            board_id=board.id,
            actor_id=user.id,
        )
    db.session.delete(column)
