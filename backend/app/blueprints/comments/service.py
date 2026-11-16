from typing import Any

from sqlalchemy import select

from app.common.access import CardAccess, CommentAccess
from app.common.constants import ActivityAction, NotificationType
from app.common.db import commit_or_conflict
from app.common.events import (
    create_notification,
    fit_message,
    log_activity,
    message_comment_added,
)
from app.extensions import db
from app.models.board import BoardMember
from app.models.comment import Comment
from app.models.user import User


def create_comment(user: User, access: CardAccess, data: dict[str, Any]) -> Comment:
    card = access.card
    board_id = access.board_id
    comment = Comment(card_id=card.id, user_id=user.id, body=data["content"])
    db.session.add(comment)
    db.session.flush()
    log_activity(board_id, user.id, ActivityAction.COMMENT_ADDED, card.id)

    candidates = {
        uid
        for uid in (card.created_by, card.assignee_id)
        if uid is not None and uid != user.id
    }
    if candidates:
        members = (
            db.session.execute(
                select(BoardMember.user_id).where(
                    BoardMember.board_id == board_id,
                    BoardMember.user_id.in_(candidates),
                )
            )
            .scalars()
            .all()
        )
        message = fit_message(message_comment_added, card.title)
        for uid in sorted(set(members), key=str):
            create_notification(
                uid, board_id, NotificationType.COMMENT_ADDED, message, card.id
            )

    commit_or_conflict()
    db.session.refresh(comment)
    return comment


def list_comments(access: CardAccess) -> list[Comment]:
    return list(
        db.session.execute(
            select(Comment)
            .where(Comment.card_id == access.card.id, Comment.deleted_at.is_(None))
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
        .scalars()
        .all()
    )


def update_comment(
    user: User, access: CommentAccess, data: dict[str, Any]
) -> Comment:
    comment = access.comment
    comment.body = data["content"]
    commit_or_conflict()
    db.session.refresh(comment)
    return comment


def delete_comment(user: User, access: CommentAccess) -> dict[str, Any]:
    comment = access.comment
    comment.soft_delete()
    commit_or_conflict()
    return {"id": comment.id}
