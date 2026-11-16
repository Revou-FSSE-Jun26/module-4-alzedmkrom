from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.common.access import CardAccess, ColumnAccess
from app.common.constants import ActivityAction, NotificationType
from app.common.db import commit_or_conflict, lock_board
from app.common.errors import NotFound, ValidationFailed
from app.common.events import (
    create_notification,
    fit_message,
    log_activity,
    message_card_assigned,
    message_card_moved,
)
from app.common.ordering import next_order, plan_move
from app.extensions import db
from app.models.board import BoardMember
from app.models import queries
from app.models.card import Card
from app.models.column import BoardColumn
from app.models.user import User


def _require_board_member(board_id: UUID, assignee_id: UUID) -> None:
    found = db.session.execute(
        select(BoardMember.user_id).where(
            BoardMember.board_id == board_id, BoardMember.user_id == assignee_id
        )
    ).first()
    if found is None:
        raise ValidationFailed({"assignee_id": ["Not a member of this board."]})


def _notify_assigned(user: User, board_id: UUID, card: Card) -> None:
    create_notification(
        card.assignee_id,
        board_id,
        NotificationType.CARD_ASSIGNED,
        fit_message(message_card_assigned, card.title),
        card.id,
    )


def create_card(user: User, access: ColumnAccess, data: dict[str, Any]) -> Card:
    board_id = access.board_id
    lock_board(board_id)
    assignee_id = data.get("assignee_id")
    if assignee_id is not None:
        _require_board_member(board_id, assignee_id)
    siblings = db.session.execute(
        select(Card.order).where(
            Card.column_id == access.column.id, Card.deleted_at.is_(None)
        )
    ).scalars()
    card = Card(
        column_id=access.column.id,
        title=data["title"],
        description=data.get("description"),
        assignee_id=assignee_id,
        created_by=user.id,
        order=next_order(siblings),
    )
    db.session.add(card)
    db.session.flush()
    log_activity(board_id, user.id, ActivityAction.CARD_CREATED, card.id)
    if assignee_id is not None and assignee_id != user.id:
        _notify_assigned(user, board_id, card)
    commit_or_conflict()
    db.session.refresh(card)
    return card


def update_card(user: User, access: CardAccess, data: dict[str, Any]) -> Card:
    card = access.card
    board_id = access.board_id
    lock_board(board_id)

    previous_assignee = card.assignee_id
    if data.get("assignee_id") is not None:
        _require_board_member(board_id, data["assignee_id"])

    changed = False
    for key in ("title", "description", "assignee_id"):
        if key in data and data[key] != getattr(card, key):
            setattr(card, key, data[key])
            changed = True

    completed_now = False
    if "completed" in data:
        if data["completed"]:
            if card.completed_at is None:
                card.completed_at = datetime.now(timezone.utc)
                completed_now = True
        else:
            card.completed_at = None

    if completed_now:
        log_activity(board_id, user.id, ActivityAction.CARD_COMPLETED, card.id)
    if changed:
        log_activity(board_id, user.id, ActivityAction.CARD_UPDATED, card.id)
    if (
        card.assignee_id is not None
        and card.assignee_id != previous_assignee
        and card.assignee_id != user.id
    ):
        _notify_assigned(user, board_id, card)

    commit_or_conflict()
    db.session.refresh(card)
    return card


def delete_card(user: User, access: CardAccess) -> dict[str, Any]:
    card = access.card
    card.soft_delete()
    log_activity(access.board_id, user.id, ActivityAction.CARD_DELETED, card.id)
    commit_or_conflict()
    return {"id": card.id}


def move_card(user: User, access: CardAccess, data: dict[str, Any]) -> dict[str, Any]:
    card = access.card
    board_id = access.board_id
    target = db.session.execute(
        select(BoardColumn).where(
            BoardColumn.id == data["column_id"],
            BoardColumn.board_id == board_id,
            BoardColumn.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if target is None:
        raise NotFound()

    lock_board(board_id)
    siblings = list(
        db.session.execute(
            select(Card).where(
                Card.column_id == target.id,
                Card.deleted_at.is_(None),
                Card.id != card.id,
            )
        )
        .scalars()
        .all()
    )
    plan = plan_move(
        [(s.id, s.order) for s in siblings], card.id, data["order"]
    )

    column_changed = card.column_id != target.id
    card.column_id = target.id
    card.order = plan.orders[card.id]
    for sibling in siblings:
        new_order = plan.orders.get(sibling.id)
        if new_order is not None and new_order != sibling.order:
            sibling.order = new_order

    if column_changed:
        log_activity(board_id, user.id, ActivityAction.CARD_MOVED, card.id)
        if card.assignee_id is not None and card.assignee_id != user.id:
            create_notification(
                card.assignee_id,
                board_id,
                NotificationType.CARD_MOVED,
                fit_message(
                    lambda title: message_card_moved(title, target.title), card.title
                ),
                card.id,
            )

    commit_or_conflict()
    db.session.refresh(card)
    result: dict[str, Any] = {
        "id": card.id,
        "column_id": card.column_id,
        "title": card.title,
        "description": card.description,
        "assignee_id": card.assignee_id,
        "created_by": card.created_by,
        "order": card.order,
        "completed_at": card.completed_at,
        "created_at": card.created_at,
        "updated_at": card.updated_at,
        "rebalanced": plan.rebalanced,
    }
    if plan.rebalanced:
        ordered = sorted([card, *siblings], key=lambda c: (c.order, c.id))
        result["siblings"] = [{"id": c.id, "order": c.order} for c in ordered]
    return result


def list_my_tasks(user: User) -> list[dict[str, Any]]:
    groups: dict[UUID, dict[str, Any]] = {}
    for board_id, board_name, card in queries.my_tasks(user.id):
        group = groups.setdefault(
            board_id, {"board_id": board_id, "board_name": board_name, "cards": []}
        )
        group["cards"].append(card)
    return list(groups.values())


def search(user: User, term: str) -> list[Card]:
    return list(queries.search_cards(term, user_id=user.id))
