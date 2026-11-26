"""Comments on live cards (BE-AZ-02, BE-AZ-05, BE-NTF-01)."""
from sqlalchemy.orm import selectinload

from app.blueprints.comments.schema import CommentCreateSchema, CommentUpdateSchema
from app.blueprints.notifications.service import notify
from app.errors import NotFound
from app.extensions import db
from app.models import Comment
from app.permissions import authorize, load_board, load_card
from app.schemas import parse
from app.transactions import transactional


def list_comments(user, card_id):
    card = load_card(card_id)
    board = load_board(card.board_id)
    authorize(user, "board:read", board)
    return (
        Comment.query.options(selectinload(Comment.author))
        .filter(Comment.card_id == card.id)
        .order_by(Comment.created_at, Comment.id)
        .all()
    )


@transactional
def create_comment(user, card_id, payload):
    card = load_card(card_id)
    board = load_board(card.board_id)
    authorize(user, "comment:create", board)
    data = parse(CommentCreateSchema, payload)
    comment = Comment(card_id=card.id, content=data["content"], created_by=user.id)
    db.session.add(comment)
    db.session.flush()
    if card.assignee_id is not None:
        notify(
            [card.assignee_id],
            type="comment_added",
            message=f'New comment on the card "{card.title}".',
            board_id=board.id,
            actor_id=user.id,
        )
    return comment


def _load_comment_for_change(user, comment_id):
    """Returns (comment, board) and enforces the comment:modify rule."""
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        raise NotFound()
    card = load_card(comment.card_id)
    board = load_board(card.board_id)
    authorize(user, "comment:modify", board, comment)
    return comment


@transactional
def update_comment(user, comment_id, payload):
    comment = _load_comment_for_change(user, comment_id)
    data = parse(CommentUpdateSchema, payload)
    comment.content = data["content"]
    return comment


@transactional
def delete_comment(user, comment_id):
    comment = _load_comment_for_change(user, comment_id)
    db.session.delete(comment)
