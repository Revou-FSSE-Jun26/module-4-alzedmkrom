from typing import Any

from sqlalchemy import func, select

from app.common.db import commit_or_conflict
from app.common.errors import NotFound
from app.common.validation import parse_uuid
from app.extensions import db
from app.models import queries
from app.models.board import Board
from app.models.column import BoardColumn
from app.models.card import Card
from app.models.notification import Notification
from app.models.user import User


def _to_dict(notification: Notification, card_id: Any) -> dict[str, Any]:
    # A dict, so masking card_id never dirties the ORM object.
    return {
        "id": notification.id,
        "type": notification.type,
        "message": notification.message,
        "board_id": notification.board_id,
        "card_id": card_id,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


def _live_card_ids(card_ids: set) -> set:
    if not card_ids:
        return set()
    return set(
        db.session.scalars(
            select(Card.id)
            .join(BoardColumn, Card.column_id == BoardColumn.id)
            .join(Board, BoardColumn.board_id == Board.id)
            .where(
                Card.id.in_(card_ids),
                Card.deleted_at.is_(None),
                BoardColumn.deleted_at.is_(None),
                Board.deleted_at.is_(None),
            )
        ).all()
    )


def list_notifications(user: User, page: int, per_page: int) -> dict[str, Any]:
    rows = queries.notifications_page(user.id, per_page, (page - 1) * per_page)
    total = db.session.scalar(
        select(func.count(Notification.id)).where(Notification.user_id == user.id)
    )
    live = _live_card_ids({n.card_id for n in rows if n.card_id is not None})
    items = [_to_dict(n, n.card_id if n.card_id in live else None) for n in rows]
    return {"items": items, "page": page, "per_page": per_page, "total": total}


def mark_read(user: User, raw_id: str) -> dict[str, Any]:
    notification = db.session.get(Notification, parse_uuid(raw_id))
    if notification is None or notification.user_id != user.id:
        raise NotFound()
    if not notification.is_read:
        notification.is_read = True
        commit_or_conflict()
        db.session.refresh(notification)
    live = _live_card_ids(
        {notification.card_id} if notification.card_id is not None else set()
    )
    card_id = notification.card_id if notification.card_id in live else None
    return _to_dict(notification, card_id)
