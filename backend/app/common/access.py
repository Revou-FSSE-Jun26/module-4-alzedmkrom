"""Record lookup plus board membership checks (Requirement 17).

Each ``get_*_for_user`` runs one joined query. No row means 404. A row whose
role is ``NULL`` means the caller is not a member, which is 403.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, select

from app.common.constants import Role
from app.common.errors import Forbidden, NotFound
from app.common.validation import parse_uuid
from app.extensions import db
from app.models.board import Board, BoardMember
from app.models.card import Card
from app.models.column import BoardColumn
from app.models.comment import Comment


@dataclass(frozen=True)
class BoardAccess:
    board_id: UUID
    role: str
    is_admin: bool


@dataclass(frozen=True)
class ColumnAccess:
    column: BoardColumn
    board_id: UUID
    role: str
    is_admin: bool


@dataclass(frozen=True)
class CardAccess:
    card: Card
    board_id: UUID
    role: str
    is_admin: bool


@dataclass(frozen=True)
class CommentAccess:
    comment: Comment
    card: Card
    board_id: UUID
    role: str
    is_admin: bool


def _member_join(user_id: UUID):
    return and_(BoardMember.board_id == Board.id, BoardMember.user_id == user_id)


def _checked_role(role: str | None) -> str:
    if role is None:
        raise Forbidden()
    return role


def get_board_for_user(user_id: UUID, raw_id: str) -> BoardAccess:
    board_id = parse_uuid(raw_id)
    row = db.session.execute(
        select(Board.id, BoardMember.role)
        .outerjoin(BoardMember, _member_join(user_id))
        .where(Board.id == board_id, Board.deleted_at.is_(None))
    ).first()
    if row is None:
        raise NotFound()
    role = _checked_role(row[1])
    return BoardAccess(row[0], role, role == Role.ADMIN.value)


def get_column_for_user(user_id: UUID, raw_id: str) -> ColumnAccess:
    column_id = parse_uuid(raw_id)
    row = db.session.execute(
        select(BoardColumn, Board.id, BoardMember.role)
        .join(Board, BoardColumn.board_id == Board.id)
        .outerjoin(BoardMember, _member_join(user_id))
        .where(
            BoardColumn.id == column_id,
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
        )
    ).first()
    if row is None:
        raise NotFound()
    role = _checked_role(row[2])
    return ColumnAccess(row[0], row[1], role, role == Role.ADMIN.value)


def get_card_for_user(user_id: UUID, raw_id: str) -> CardAccess:
    card_id = parse_uuid(raw_id)
    row = db.session.execute(
        select(Card, Board.id, BoardMember.role)
        .join(BoardColumn, Card.column_id == BoardColumn.id)
        .join(Board, BoardColumn.board_id == Board.id)
        .outerjoin(BoardMember, _member_join(user_id))
        .where(
            Card.id == card_id,
            Card.deleted_at.is_(None),
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
        )
    ).first()
    if row is None:
        raise NotFound()
    role = _checked_role(row[2])
    return CardAccess(row[0], row[1], role, role == Role.ADMIN.value)


def get_comment_for_user(user_id: UUID, raw_id: str) -> CommentAccess:
    comment_id = parse_uuid(raw_id)
    row = db.session.execute(
        select(Comment, Card, Board.id, BoardMember.role)
        .join(Card, Comment.card_id == Card.id)
        .join(BoardColumn, Card.column_id == BoardColumn.id)
        .join(Board, BoardColumn.board_id == Board.id)
        .outerjoin(BoardMember, _member_join(user_id))
        .where(
            Comment.id == comment_id,
            Comment.deleted_at.is_(None),
            Card.deleted_at.is_(None),
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
        )
    ).first()
    if row is None:
        raise NotFound()
    role = _checked_role(row[3])
    return CommentAccess(row[0], row[1], row[2], role, role == Role.ADMIN.value)


def require_admin(access) -> None:
    if access.role != Role.ADMIN.value:
        raise Forbidden()


def require_admin_or_self(access: BoardAccess, user_id: UUID, target: UUID) -> None:
    if access.role != Role.ADMIN.value and user_id != target:
        raise Forbidden()


def require_card_deleter(access: CardAccess, user_id: UUID) -> None:
    if access.role != Role.ADMIN.value and access.card.created_by != user_id:
        raise Forbidden()


def require_comment_owner(access: CommentAccess, user_id: UUID) -> None:
    if access.comment.user_id != user_id:
        raise Forbidden()
