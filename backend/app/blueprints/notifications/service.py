"""Notification creation and reads (BE-NTF-01, BE-NTF-02, BE-NTF-03).

`notify` is the only place that writes notification rows. It runs inside the
caller's transaction. The notifications.type CHECK in the database accepts only
the four values in STORED_TYPES. Other triggers listed in BE-NTF-01 cannot be stored
and are not emitted (see the final report).
"""
from sqlalchemy import func, select

from app.errors import NotFound
from app.extensions import db
from app.models import Notification
from app.pagination import paginate

STORED_TYPES = frozenset({"card_assigned", "card_moved", "comment_added", "member_added"})
MESSAGE_MAX = 500


def notify(recipient_ids, *, type, message, board_id, actor_id):
    """Add one row per distinct recipient, skipping the actor. Does not commit."""
    if type not in STORED_TYPES:
        raise ValueError(f"Notification type {type!r} is not allowed by the database CHECK.")
    seen = set()
    for user_id in recipient_ids:
        if user_id is None or user_id == actor_id or user_id in seen:
            continue
        seen.add(user_id)
        db.session.add(
            Notification(
                user_id=user_id,
                type=type,
                message=message[:MESSAGE_MAX],
                board_id=board_id,
            )
        )


def list_notifications(user, page, per_page):
    query = (
        Notification.query.filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    items, total, pages = paginate(query, page, per_page)
    unread = db.session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id, Notification.is_read.is_(False)
        )
    )
    return items, total, pages, unread


def mark_read(user, notification_id):
    notification = db.session.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise NotFound()
    notification.is_read = True
    db.session.commit()
    return notification
