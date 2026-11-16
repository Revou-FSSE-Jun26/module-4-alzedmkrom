from typing import Callable
from uuid import UUID

from app.common.constants import (
    NOTIFICATION_MESSAGE_MAX,
    ActivityAction,
    NotificationType,
)
from app.extensions import db
from app.models.activity_log import ActivityLog
from app.models.notification import Notification

ELLIPSIS = "…"


def log_activity(
    board_id: UUID,
    user_id: UUID,
    action: ActivityAction,
    card_id: UUID | None = None,
) -> None:
    """Add an activity row to the caller's transaction (no flush, no commit)."""
    db.session.add(
        ActivityLog(
            board_id=board_id,
            user_id=user_id,
            card_id=card_id,
            action=ActivityAction(action).value,
        )
    )


def create_notification(
    user_id: UUID,
    board_id: UUID,
    type_: NotificationType,
    message: str,
    card_id: UUID | None = None,
) -> None:
    """Add a notification row to the caller's transaction (no flush, no commit)."""
    db.session.add(
        Notification(
            user_id=user_id,
            board_id=board_id,
            card_id=card_id,
            type=NotificationType(type_).value,
            message=message,
        )
    )


def fit_message(
    render: Callable[[str], str], title: str, limit: int = NOTIFICATION_MESSAGE_MAX
) -> str:
    """render(title) when it fits, otherwise a truncated title ending in '…'."""
    message = render(title)
    if len(message) <= limit:
        return message
    keep = min(len(title), max(0, limit - len(render(ELLIPSIS))))
    while keep >= 0:
        message = render(title[:keep] + ELLIPSIS)
        if len(message) <= limit:
            return message
        keep -= 1
    return message[:limit]  # pragma: no cover - template alone exceeds the limit


def message_card_assigned(title: str) -> str:
    return f'You were assigned to "{title}"'


def message_card_moved(title: str, column_title: str) -> str:
    return f'"{title}" was moved to "{column_title}"'


def message_comment_added(title: str) -> str:
    return f'New comment on "{title}"'


def message_member_added(board_name: str) -> str:
    return f'You were added to board "{board_name}"'
