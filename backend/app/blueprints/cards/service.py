"""Card create, edit, move, soft delete and the assigned-tasks list (BE-SVC-05, BE-SVC-06, BE-ORD-03)."""
from datetime import datetime, timezone

from sqlalchemy import and_, func

from app.blueprints.cards.schema import (
    AssignedCardsQuerySchema,
    CardCreateSchema,
    CardPositionSchema,
    CardUpdateSchema,
)
from app.blueprints.notifications.service import notify
from app.errors import ValidationFailed
from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card
from app.ordering import end_order, plan_order
from app.pagination import paginate
from app.permissions import authorize, board_admin_ids, load_board, load_card, load_column
from app.schemas import parse
from app.transactions import lock_board, transactional


def _require_board_member(board_id, user_id):
    if user_id is None:
        return
    if db.session.get(BoardMember, (board_id, user_id)) is None:
        raise ValidationFailed(details={"assignee_id": ["User is not a member of this board."]})


@transactional
def create_card(user, column_id, payload):
    column = load_column(column_id)
    board = load_board(column.board_id)
    authorize(user, "card:create", board)
    data = parse(CardCreateSchema, payload)
    assignee_id = data.get("assignee_id")
    _require_board_member(board.id, assignee_id)
    lock_board(board.id)
    last = Card.active().with_entities(func.max(Card.order)).filter(Card.column_id == column.id).scalar()
    card = Card(
        board_id=board.id,
        column_id=column.id,
        title=data["title"],
        description=data.get("description"),
        assignee_id=assignee_id,
        due_date=data.get("due_date"),
        order=end_order(last),
        completed_at=datetime.now(timezone.utc) if column.is_done else None,
        created_by=user.id,
    )
    db.session.add(card)
    db.session.flush()
    admin_ids = [a for a in board_admin_ids(board.id) if a != assignee_id]
    notify(
        admin_ids,
        type="card_created",
        message=f'A card "{card.title}" was created.',
        board_id=board.id,
        actor_id=user.id,
    )
    if assignee_id is not None:
        notify(
            [assignee_id],
            type="card_assigned",
            message=f'You were assigned the card "{card.title}".',
            board_id=board.id,
            actor_id=user.id,
        )
    return card


@transactional
def update_card(user, card_id, payload):
    card = load_card(card_id)
    board = load_board(card.board_id)
    authorize(user, "card:update", board)
    data = parse(CardUpdateSchema, payload)
    if "assignee_id" in data:
        _require_board_member(board.id, data["assignee_id"])
    previous_assignee = card.assignee_id
    for field in ("title", "description", "due_date", "assignee_id"):
        if field in data:
            setattr(card, field, data[field])
    new_assignee = data.get("assignee_id")
    if new_assignee is not None and new_assignee != previous_assignee:
        notify(
            [new_assignee],
            type="card_assigned",
            message=f'You were assigned the card "{card.title}".',
            board_id=board.id,
            actor_id=user.id,
        )
    return card


@transactional
def move_card(user, card_id, payload):
    card = load_card(card_id)
    board = load_board(card.board_id)
    authorize(user, "card:move", board)
    data = parse(CardPositionSchema, payload)
    target = db.session.get(BoardColumn, data["column_id"])
    if target is None or target.board_id != board.id:
        reason = "Column belongs to a different board." if target else "Column does not exist."
        raise ValidationFailed(details={"column_id": [reason]})

    lock_board(board.id)
    from_column = card.column_id
    cards_in_target = (
        Card.active()
        .filter(Card.column_id == target.id)
        .order_by(Card.order, Card.id)
        .all()
    )
    placement = plan_order([(c.id, c.order) for c in cards_in_target], card.id, data["order"])
    by_id = {c.id: c for c in cards_in_target}
    by_id[card.id] = card
    card.column_id = target.id
    for card_key, new_order in placement.orders.items():
        by_id[card_key].order = new_order

    if target.is_done:
        if card.completed_at is None:
            card.completed_at = datetime.now(timezone.utc)
    else:
        card.completed_at = None

    if from_column != target.id:
        notify(
            board_admin_ids(board.id),
            type="card_moved",
            message=f'The card "{card.title}" was moved to "{target.name}".',
            board_id=board.id,
            actor_id=user.id,
        )
    return card, placement


@transactional
def delete_card(user, card_id):
    """Soft delete (BE-SVC-06). The row stays with deleted_at set."""
    card = load_card(card_id)
    board = load_board(card.board_id)
    authorize(user, "card:delete", board, card)
    creator = card.created_by
    title = card.title
    admin_ids = [a for a in board_admin_ids(board.id) if a != creator]
    card.soft_delete()
    if creator is not None and creator != user.id:
        notify(
            [creator],
            type="card_deleted",
            message=f'Your card "{title}" was deleted by an administrator.',
            board_id=board.id,
            actor_id=user.id,
        )
    notify(
        admin_ids,
        type="card_deleted",
        message=f'The card "{title}" was deleted.',
        board_id=board.id,
        actor_id=user.id,
    )


def list_assigned(user, payload):
    args = parse(AssignedCardsQuerySchema, payload)
    query = (
        Card.active()
        .join(BoardColumn, BoardColumn.id == Card.column_id)
        .join(Board, Board.id == Card.board_id)
        .join(
            BoardMember,
            and_(BoardMember.board_id == Card.board_id, BoardMember.user_id == user.id),
        )
        .with_entities(Card, BoardColumn.name, Board.name)
        .filter(Card.assignee_id == user.id)
    )
    if "board_id" in args:
        query = query.filter(Card.board_id == args["board_id"])
    if "done" in args:
        query = query.filter(
            Card.completed_at.isnot(None) if args["done"] else Card.completed_at.is_(None)
        )
    query = query.order_by(Board.name, BoardColumn.order, Card.order, Card.id)
    rows, total, pages = paginate(query, args["page"], args["per_page"])
    return rows, args["page"], args["per_page"], total, pages
